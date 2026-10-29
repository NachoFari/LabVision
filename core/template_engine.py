"""
LabVision - Template Engine
===========================
Scientific template manager and Sub-ROI extraction engine for laboratory instruments.
Supports loading, validating, saving, importing, exporting, and cropping sub-regions
from standardized .lvtemplate packages.

Architecture Provenance:
- Compliant with LabVision Universal Roadmap v0.9 (Work Package 1).
- Designed for fault-tolerant, offline-first laboratory workstation operation.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

# Set up logger for defensive tracing
logger = logging.getLogger("LabVision.TemplateEngine")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Base directory dynamically resolved relative to this module
# Strictly relative to codebase root (no hardcoded absolute drive letters)
BASE_DIR: Path = Path(__file__).resolve().parent.parent
DEFAULT_PRESETS_DIR: Path = BASE_DIR / "templates" / "presets"
DEFAULT_CUSTOM_DIR: Path = BASE_DIR / "templates" / "custom"

TEMPLATE_EXTENSION: str = ".lvtemplate"
CURRENT_TEMPLATE_VERSION: str = "1.0"


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class LabVisionTemplateError(Exception):
    """Base exception for all LabVision template operations."""
    pass


class TemplateNotFoundError(LabVisionTemplateError, FileNotFoundError):
    """Raised when a template file or template ID cannot be located on disk."""
    pass


class TemplateCorruptError(LabVisionTemplateError, ValueError):
    """Raised when a template file is malformed JSON or unreadable."""
    pass


class TemplateValidationError(LabVisionTemplateError, ValueError):
    """Raised when a template fails structural or coordinate schema validation."""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors: List[str] = errors or []


# ==============================================================================
# Validation Logic
# ==============================================================================

def validate_template(data: Any, raise_on_error: bool = False) -> Tuple[bool, List[str]]:
    """
    Validates the structure and scientific parameters of a .lvtemplate data dictionary.

    Parameters
    ----------
    data : Any
        Parsed JSON object representing the template.
    raise_on_error : bool, default=False
        If True, raises TemplateValidationError when invalid.

    Returns
    -------
    Tuple[bool, List[str]]
        (is_valid, list_of_error_messages)

    Scientific Parameter Rules:
    - Metadata must declare unique template_id and human-readable instrument name.
    - sub_rois must contain >= 1 field.
    - Each sub-ROI must specify relative coordinates (x, y, w, h) in [0.0, 1.0].
    - Coordinate boundary sum (x + w) and (y + h) must not exceed 1.001 (floating tolerance).
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        errors.append("El contenido de la plantilla debe ser un objeto JSON (dict).")
        if raise_on_error:
            raise TemplateValidationError("Plantilla inválida", errors=errors)
        return False, errors

    # Check version
    version = data.get("lvtemplate_version")
    if not version:
        errors.append("Falta el campo requerido 'lvtemplate_version'.")

    # Check metadata
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("Falta la sección requerida 'metadata' (debe ser un objeto).")
    else:
        template_id = metadata.get("template_id")
        if not template_id or not isinstance(template_id, str):
            errors.append("metadata.template_id es obligatorio y debe ser un texto identificador.")
        elif not re.match(r"^[a-zA-Z0-9_\-]+$", template_id):
            errors.append(f"metadata.template_id '{template_id}' contiene caracteres no permitidos (solo a-z, 0-9, _, -).")

        name = metadata.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append("metadata.name es obligatorio y debe ser una cadena no vacía.")

    # Check display profile
    display_profile = data.get("display_profile")
    if display_profile is not None and not isinstance(display_profile, dict):
        errors.append("'display_profile' debe ser un objeto si está presente.")

    # Check sub_rois
    sub_rois = data.get("sub_rois")
    if not isinstance(sub_rois, list):
        errors.append("La sección 'sub_rois' es obligatoria y debe ser una lista de regiones.")
    elif len(sub_rois) == 0:
        errors.append("La plantilla debe contener al menos un sub-ROI en 'sub_rois'.")
    else:
        seen_ids = set()
        for idx, roi in enumerate(sub_rois):
            if not isinstance(roi, dict):
                errors.append(f"sub_rois[{idx}] debe ser un objeto descriptivo de región.")
                continue

            roi_id = roi.get("id")
            if not roi_id or not isinstance(roi_id, str):
                errors.append(f"sub_rois[{idx}].id es obligatorio y debe ser texto.")
            elif roi_id in seen_ids:
                errors.append(f"sub_rois[{idx}].id '{roi_id}' está duplicado dentro de la plantilla.")
            else:
                seen_ids.add(roi_id)

            label = roi.get("display_label")
            if not label or not isinstance(label, str):
                errors.append(f"sub_rois[{idx}].display_label es obligatorio.")

            # Validate relative coordinates
            coords = roi.get("coordinates_relative")
            if not isinstance(coords, dict):
                errors.append(f"sub_rois[{idx}].coordinates_relative es obligatorio y debe ser un objeto {{x, y, w, h}}.")
            else:
                for coord_key in ("x", "y", "w", "h"):
                    val = coords.get(coord_key)
                    if val is None or not isinstance(val, (int, float)):
                        errors.append(f"sub_rois[{idx}].coordinates_relative.{coord_key} debe ser un número flotante.")

                try:
                    x = float(coords.get("x", 0.0))
                    y = float(coords.get("y", 0.0))
                    w = float(coords.get("w", 0.0))
                    h = float(coords.get("h", 0.0))

                    if not (0.0 <= x <= 1.0):
                        errors.append(f"sub_rois[{idx}] coord x={x} fuera del rango normalizado [0.0, 1.0].")
                    if not (0.0 <= y <= 1.0):
                        errors.append(f"sub_rois[{idx}] coord y={y} fuera del rango normalizado [0.0, 1.0].")
                    if not (0.0 < w <= 1.0):
                        errors.append(f"sub_rois[{idx}] ancho w={w} inválido (debe ser > 0.0 y <= 1.0).")
                    if not (0.0 < h <= 1.0):
                        errors.append(f"sub_rois[{idx}] alto h={h} inválido (debe ser > 0.0 y <= 1.0).")

                    # Tolerance check for float summing
                    if (x + w) > 1.001:
                        errors.append(f"sub_rois[{idx}] desborda el límite horizontal: x + w = {x + w:.4f} > 1.0.")
                    if (y + h) > 1.001:
                        errors.append(f"sub_rois[{idx}] desborda el límite vertical: y + h = {y + h:.4f} > 1.0.")
                except (ValueError, TypeError):
                    pass

            # Optional valid_range check
            valid_range = roi.get("valid_range")
            if valid_range is not None:
                if not isinstance(valid_range, (list, tuple)) or len(valid_range) != 2:
                    errors.append(f"sub_rois[{idx}].valid_range debe ser una lista de 2 números [min, max].")
                else:
                    try:
                        vmin = float(valid_range[0])
                        vmax = float(valid_range[1])
                        if vmin > vmax:
                            errors.append(f"sub_rois[{idx}].valid_range mínimo {vmin} es mayor que el máximo {vmax}.")
                    except (ValueError, TypeError):
                        errors.append(f"sub_rois[{idx}].valid_range contiene valores numéricos no válidos.")

    is_valid = len(errors) == 0
    if not is_valid and raise_on_error:
        raise TemplateValidationError(
            f"La plantilla no superó la validación ({len(errors)} error(es)): " + " | ".join(errors),
            errors=errors
        )

    return is_valid, errors


# ==============================================================================
# File System Operations
# ==============================================================================

def _ensure_directories(presets_dir: Optional[Path] = None, custom_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    """Ensures target template directories exist and returns their resolved Paths."""
    p_dir = Path(presets_dir or DEFAULT_PRESETS_DIR).resolve()
    c_dir = Path(custom_dir or DEFAULT_CUSTOM_DIR).resolve()
    try:
        p_dir.mkdir(parents=True, exist_ok=True)
        c_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        logger.warning(f"Error al verificar/crear carpetas de plantillas: {err}")
    return p_dir, c_dir


def list_presets(presets_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """
    Lists all official factory presets available in templates/presets.

    Parameters
    ----------
    presets_dir : Optional[Union[str, Path]]
        Optional override directory path. Defaults to templates/presets.

    Returns
    -------
    List[Dict[str, Any]]
        List of summarized preset descriptions with parsed metadata and file paths.
    """
    target_dir = Path(presets_dir or DEFAULT_PRESETS_DIR).resolve()
    if not target_dir.exists():
        logger.warning(f"Carpeta de presets no encontrada: {target_dir}")
        return []

    templates: List[Dict[str, Any]] = []
    pattern = f"*{TEMPLATE_EXTENSION}"

    for file_path in sorted(target_dir.glob(pattern)):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            is_valid, _ = validate_template(data, raise_on_error=False)
            metadata = data.get("metadata", {})
            sub_rois = data.get("sub_rois", [])

            templates.append({
                "template_id": metadata.get("template_id", file_path.stem),
                "name": metadata.get("name", file_path.stem),
                "description": metadata.get("description", ""),
                "display_type": data.get("display_profile", {}).get("type", "general"),
                "compatible_hardware": metadata.get("compatible_hardware", []),
                "author": metadata.get("author", "LabVision"),
                "institution": metadata.get("institution", ""),
                "sub_roi_count": len(sub_rois),
                "sub_rois_summary": [
                    {
                        "id": r.get("id"),
                        "label": r.get("display_label"),
                        "unit": r.get("unit", "")
                    }
                    for r in sub_rois
                ],
                "file_path": str(file_path),
                "filename": file_path.name,
                "is_preset": True,
                "is_valid": is_valid
            })
        except Exception as err:
            logger.error(f"Error leyendo archivo preset {file_path.name}: {err}")
            templates.append({
                "template_id": file_path.stem,
                "name": file_path.name,
                "description": "Error al leer o analizar archivo de plantilla",
                "file_path": str(file_path),
                "filename": file_path.name,
                "is_preset": True,
                "is_valid": False,
                "error": str(err)
            })

    return templates


def list_custom(custom_dir: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """
    Lists all user-defined custom templates available in templates/custom.

    Parameters
    ----------
    custom_dir : Optional[Union[str, Path]]
        Optional override directory path. Defaults to templates/custom.

    Returns
    -------
    List[Dict[str, Any]]
        List of summarized custom templates.
    """
    target_dir = Path(custom_dir or DEFAULT_CUSTOM_DIR).resolve()
    if not target_dir.exists():
        return []

    templates: List[Dict[str, Any]] = []
    pattern = f"*{TEMPLATE_EXTENSION}"

    for file_path in sorted(target_dir.glob(pattern)):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            is_valid, _ = validate_template(data, raise_on_error=False)
            metadata = data.get("metadata", {})
            sub_rois = data.get("sub_rois", [])

            templates.append({
                "template_id": metadata.get("template_id", file_path.stem),
                "name": metadata.get("name", file_path.stem),
                "description": metadata.get("description", ""),
                "display_type": data.get("display_profile", {}).get("type", "general"),
                "compatible_hardware": metadata.get("compatible_hardware", []),
                "author": metadata.get("author", "Usuario"),
                "institution": metadata.get("institution", ""),
                "sub_roi_count": len(sub_rois),
                "sub_rois_summary": [
                    {
                        "id": r.get("id"),
                        "label": r.get("display_label"),
                        "unit": r.get("unit", "")
                    }
                    for r in sub_rois
                ],
                "file_path": str(file_path),
                "filename": file_path.name,
                "is_preset": False,
                "is_valid": is_valid
            })
        except Exception as err:
            logger.error(f"Error leyendo plantilla personalizada {file_path.name}: {err}")
            templates.append({
                "template_id": file_path.stem,
                "name": file_path.name,
                "description": "Error al leer o analizar archivo",
                "file_path": str(file_path),
                "filename": file_path.name,
                "is_preset": False,
                "is_valid": False,
                "error": str(err)
            })

    return templates


def list_all_templates(
    presets_dir: Optional[Union[str, Path]] = None,
    custom_dir: Optional[Union[str, Path]] = None
) -> List[Dict[str, Any]]:
    """Returns a unified list of both factory presets and custom templates."""
    presets = list_presets(presets_dir)
    customs = list_custom(custom_dir)
    return presets + customs


def load_template(
    template_path_or_id: Union[str, Path],
    search_dirs: Optional[Sequence[Union[str, Path]]] = None
) -> Dict[str, Any]:
    """
    Loads and validates a .lvtemplate from disk.

    Can locate the template by:
    1. Direct file path (absolute or relative)
    2. File name with or without extension within search directories
    3. template_id inside presets or custom folders

    Parameters
    ----------
    template_path_or_id : Union[str, Path]
        Path or identifier for the template.
    search_dirs : Optional[Sequence[Union[str, Path]]]
        Directories to search within. Defaults to [custom_dir, presets_dir].

    Returns
    -------
    Dict[str, Any]
        The fully parsed and validated template dictionary with injected metadata.
    """
    raw_path = Path(template_path_or_id)
    candidate_file: Optional[Path] = None

    # 1. Direct path check
    if raw_path.is_file():
        candidate_file = raw_path
    elif raw_path.with_suffix(TEMPLATE_EXTENSION).is_file():
        candidate_file = raw_path.with_suffix(TEMPLATE_EXTENSION)

    # 2. Search in designated directories
    if candidate_file is None:
        p_dir, c_dir = _ensure_directories()
        dirs = [Path(d).resolve() for d in search_dirs] if search_dirs else [c_dir, p_dir]

        search_names = [
            str(template_path_or_id),
            f"{template_path_or_id}{TEMPLATE_EXTENSION}"
        ]

        for directory in dirs:
            if not directory.exists():
                continue
            for name in search_names:
                potential = directory / name
                if potential.is_file():
                    candidate_file = potential
                    break
            if candidate_file:
                break

        # 3. Fallback: inspect template_id in json files
        if candidate_file is None:
            for directory in dirs:
                if not directory.exists():
                    continue
                for file_path in directory.glob(f"*{TEMPLATE_EXTENSION}"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            meta = json.load(f).get("metadata", {})
                            if meta.get("template_id") == str(template_path_or_id):
                                candidate_file = file_path
                                break
                    except Exception:
                        continue
                if candidate_file:
                    break

    if candidate_file is None:
        raise TemplateNotFoundError(
            f"No se encontró la plantilla '{template_path_or_id}'. "
            f"Verifique que el archivo exista en templates/presets o templates/custom."
        )

    # Read and parse JSON
    try:
        with open(candidate_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as json_err:
        raise TemplateCorruptError(
            f"El archivo '{candidate_file.name}' está dañado o no es un JSON válido: {json_err}"
        ) from json_err
    except OSError as io_err:
        raise TemplateCorruptError(
            f"No se pudo leer el archivo '{candidate_file}': {io_err}"
        ) from io_err

    # Strict validation
    validate_template(data, raise_on_error=True)

    # Inject runtime file tracking attributes
    data["_source_path"] = str(candidate_file.resolve())
    data["_is_preset"] = "presets" in candidate_file.parts

    return data


def save_template(
    template_data: Dict[str, Any],
    filename: Optional[str] = None,
    destination: str = "custom",
    target_dir: Optional[Union[str, Path]] = None,
    overwrite: bool = True
) -> Path:
    """
    Validates and saves a template dictionary as a .lvtemplate file.

    Parameters
    ----------
    template_data : Dict[str, Any]
        Template data structure to save.
    filename : Optional[str]
        File name (e.g. 'mi_instrumento.lvtemplate'). If omitted, derived from metadata.template_id.
    destination : str, default='custom'
        Target category ('custom' or 'preset').
    target_dir : Optional[Union[str, Path]]
        Explicit directory override.
    overwrite : bool, default=True
        Whether to overwrite an existing file.

    Returns
    -------
    Path
        Path to the saved .lvtemplate file.
    """
    validate_template(template_data, raise_on_error=True)

    p_dir, c_dir = _ensure_directories()
    if target_dir:
        out_dir = Path(target_dir).resolve()
    elif destination == "preset":
        out_dir = p_dir
    else:
        out_dir = c_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename
    if not filename:
        raw_id = template_data.get("metadata", {}).get("template_id", "plantilla_sin_nombre")
        clean_id = re.sub(r"[^\w\-]", "_", str(raw_id).lower().strip())
        filename = f"{clean_id}{TEMPLATE_EXTENSION}"
    elif not filename.endswith(TEMPLATE_EXTENSION):
        filename = f"{filename}{TEMPLATE_EXTENSION}"

    target_file = out_dir / filename

    if target_file.exists() and not overwrite:
        raise FileExistsError(f"El archivo '{target_file}' ya existe y overwrite=False.")

    # Remove runtime internal keys before saving
    clean_data = {k: v for k, v in template_data.items() if not k.startswith("_")}

    # Atomic write pattern using temporary file
    temp_file = target_file.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(clean_data, f, indent=2, ensure_ascii=False)
        temp_file.replace(target_file)
    except Exception as e:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass
        raise OSError(f"Error escribiendo plantilla en '{target_file}': {e}") from e

    logger.info(f"Plantilla guardada exitosamente: {target_file}")
    return target_file


def import_template(
    source_file_path: Union[str, Path],
    target_dir: Optional[Union[str, Path]] = None,
    overwrite: bool = False
) -> Path:
    """
    Imports an external .lvtemplate file, validates it, and installs it into custom templates.

    Parameters
    ----------
    source_file_path : Union[str, Path]
        Path to the external template file.
    target_dir : Optional[Union[str, Path]]
        Target custom directory. Defaults to templates/custom.
    overwrite : bool, default=False
        Whether to overwrite an existing custom template.

    Returns
    -------
    Path
        Path to the newly installed template in the custom directory.
    """
    src = Path(source_file_path).resolve()
    if not src.is_file():
        raise TemplateNotFoundError(f"Archivo de origen para importación no existe: {src}")

    # Validate source before importing
    try:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise TemplateCorruptError(f"No se pudo leer el archivo a importar: {e}") from e

    validate_template(data, raise_on_error=True)

    _, c_dir = _ensure_directories(custom_dir=target_dir)
    dest_file = c_dir / src.name

    if dest_file.exists() and not overwrite:
        raise FileExistsError(f"La plantilla personalizada '{src.name}' ya existe en '{c_dir}'.")

    shutil.copy2(src, dest_file)
    logger.info(f"Plantilla importada correctamente hacia: {dest_file}")
    return dest_file


def export_template(
    template_id_or_path: Union[str, Path],
    destination_path: Union[str, Path],
    overwrite: bool = True
) -> Path:
    """
    Exports a template (preset or custom) to an external file path.

    Parameters
    ----------
    template_id_or_path : Union[str, Path]
        Template identifier or file path.
    destination_path : Union[str, Path]
        Target destination path for the exported .lvtemplate file.
    overwrite : bool, default=True
        Whether to overwrite an existing destination file.

    Returns
    -------
    Path
        Path of the exported file.
    """
    template_data = load_template(template_id_or_path)
    dest = Path(destination_path).resolve()

    if not dest.name.endswith(TEMPLATE_EXTENSION):
        dest = dest.with_name(f"{dest.name}{TEMPLATE_EXTENSION}")

    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists() and not overwrite:
        raise FileExistsError(f"El destino de exportación ya existe: {dest}")

    clean_data = {k: v for k, v in template_data.items() if not k.startswith("_")}
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Plantilla exportada a: {dest}")
    return dest


# ==============================================================================
# Computer Vision: Sub-ROI Cropping Engine
# ==============================================================================

def crop_sub_rois(
    frame: np.ndarray,
    template_or_sub_rois: Union[Dict[str, Any], Sequence[Dict[str, Any]]],
    parent_roi: Optional[Sequence[int]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Cuts and extracts individual sub-ROIs from a camera or video frame based on
    normalized relative coordinates defined in the template.

    Parameters
    ----------
    frame : np.ndarray
        Input image frame (BGR, RGB or Grayscale uint8 array).
    template_or_sub_rois : Union[Dict[str, Any], Sequence[Dict[str, Any]]]
        Either the loaded template dictionary or directly the 'sub_rois' list.
    parent_roi : Optional[Sequence[int]]
        Optional [x, y, w, h] bounding box in pixel coordinates defining the instrument
        display panel inside `frame`. If None, relative coordinates apply to the whole frame.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of `sub_roi_id` -> {
            "id": str,
            "display_label": str,
            "unit": str,
            "crop": np.ndarray,
            "pixel_bbox": Tuple[int, int, int, int],  # (abs_x, abs_y, w, h)
            "relative_bbox": Tuple[float, float, float, float],  # (x, y, w, h)
            "data_type": str,
            "ocr_whitelist": str,
            "valid_range": Optional[List[float]],
            "decimal_places": Optional[int],
            "quality_alert_on_jump": Optional[float]
        }

    Scientific Fault-Tolerance:
    - Never crashes on None, empty frames, zero-size crops, or malformed ROIs.
    - Slices are strictly clamped to frame boundaries.
    - Returns empty dict cleanly if frame or coordinates are invalid.
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        logger.warning("crop_sub_rois recibió un fotograma nulo o vacío.")
        return {}

    if frame.ndim not in (2, 3):
        logger.warning(f"Dimensión de fotograma no soportada: {frame.ndim}")
        return {}

    frame_h, frame_w = frame.shape[:2]
    if frame_h <= 0 or frame_w <= 0:
        return {}

    # Extract sub_rois list
    if isinstance(template_or_sub_rois, dict):
        sub_rois = template_or_sub_rois.get("sub_rois", [])
    elif isinstance(template_or_sub_rois, (list, tuple)):
        sub_rois = list(template_or_sub_rois)
    else:
        logger.warning("template_or_sub_rois debe ser un diccionario de plantilla o lista de regiones.")
        return {}

    # 1. Determine base reference panel (screen crop)
    offset_x: int = 0
    offset_y: int = 0

    if parent_roi is not None and len(parent_roi) == 4:
        try:
            px, py, pw, ph = [int(round(v)) for v in parent_roi]
            x1 = max(0, min(frame_w, px))
            y1 = max(0, min(frame_h, py))
            x2 = max(0, min(frame_w, px + max(1, pw)))
            y2 = max(0, min(frame_h, py + max(1, ph)))

            if x2 > x1 and y2 > y1:
                screen_crop = frame[y1:y2, x1:x2]
                offset_x = x1
                offset_y = y1
            else:
                screen_crop = frame
        except Exception as e:
            logger.warning(f"Error procesando parent_roi {parent_roi}: {e}. Usando fotograma completo.")
            screen_crop = frame
    else:
        screen_crop = frame

    screen_h, screen_w = screen_crop.shape[:2]
    if screen_h <= 0 or screen_w <= 0:
        return {}

    # 2. Extract each sub-ROI
    extracted: Dict[str, Dict[str, Any]] = {}

    for idx, roi in enumerate(sub_rois):
        if not isinstance(roi, dict):
            continue

        roi_id = str(roi.get("id", f"region_{idx}"))
        coords = roi.get("coordinates_relative", {})
        if not isinstance(coords, dict):
            continue

        try:
            rx = float(coords.get("x", 0.0))
            ry = float(coords.get("y", 0.0))
            rw = float(coords.get("w", 1.0))
            rh = float(coords.get("h", 1.0))
        except (ValueError, TypeError):
            continue

        # Clamp relative coordinates to [0.0, 1.0] defensively
        rx = max(0.0, min(1.0, rx))
        ry = max(0.0, min(1.0, ry))
        rw = max(0.0, min(1.0 - rx, rw))
        rh = max(0.0, min(1.0 - ry, rh))

        # Convert to screen pixel coordinates
        sub_px = int(round(rx * screen_w))
        sub_py = int(round(ry * screen_h))
        sub_pw = max(1, int(round(rw * screen_w)))
        sub_ph = max(1, int(round(rh * screen_h)))

        # Absolute boundaries clamped to screen crop
        cx1 = max(0, min(screen_w, sub_px))
        cy1 = max(0, min(screen_h, sub_py))
        cx2 = max(cx1 + 1, min(screen_w, sub_px + sub_pw))
        cy2 = max(cy1 + 1, min(screen_h, sub_py + sub_ph))

        # Perform crop safely
        crop_img = screen_crop[cy1:cy2, cx1:cx2].copy()

        # Absolute coordinates relative to original frame
        abs_x = offset_x + cx1
        abs_y = offset_y + cy1
        abs_w = cx2 - cx1
        abs_h = cy2 - cy1

        extracted[roi_id] = {
            "id": roi_id,
            "display_label": roi.get("display_label", roi_id),
            "unit": roi.get("unit", ""),
            "crop": crop_img,
            "pixel_bbox": (abs_x, abs_y, abs_w, abs_h),
            "relative_bbox": (rx, ry, rw, rh),
            "data_type": roi.get("data_type", "float"),
            "ocr_whitelist": roi.get("ocr_whitelist", ""),
            "valid_range": roi.get("valid_range"),
            "decimal_places": roi.get("decimal_places"),
            "quality_alert_on_jump": roi.get("quality_alert_on_jump")
        }

    return extracted


# ==============================================================================
# Object-Oriented Manager Wrapper
# ==============================================================================

class TemplateEngine:
    """
    High-level Object-Oriented Manager for LabVision Instrument Templates.
    Can be instantiated with custom paths or used with default workspace locations.
    """
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        self.base_dir = Path(base_dir).resolve() if base_dir else BASE_DIR
        self.presets_dir = self.base_dir / "templates" / "presets"
        self.custom_dir = self.base_dir / "templates" / "custom"
        _ensure_directories(self.presets_dir, self.custom_dir)

    def list_presets(self) -> List[Dict[str, Any]]:
        return list_presets(self.presets_dir)

    def list_custom(self) -> List[Dict[str, Any]]:
        return list_custom(self.custom_dir)

    def list_all(self) -> List[Dict[str, Any]]:
        return list_all_templates(self.presets_dir, self.custom_dir)

    def load(self, template_id_or_path: Union[str, Path]) -> Dict[str, Any]:
        return load_template(template_id_or_path, search_dirs=[self.custom_dir, self.presets_dir])

    def save(
        self,
        template_data: Dict[str, Any],
        filename: Optional[str] = None,
        destination: str = "custom",
        overwrite: bool = True
    ) -> Path:
        target = self.presets_dir if destination == "preset" else self.custom_dir
        return save_template(template_data, filename=filename, target_dir=target, overwrite=overwrite)

    def import_template(self, source_path: Union[str, Path], overwrite: bool = False) -> Path:
        return import_template(source_path, target_dir=self.custom_dir, overwrite=overwrite)

    def export_template(
        self,
        template_id_or_path: Union[str, Path],
        dest_path: Union[str, Path],
        overwrite: bool = True
    ) -> Path:
        return export_template(template_id_or_path, destination_path=dest_path, overwrite=overwrite)

    def crop(
        self,
        frame: np.ndarray,
        template_or_sub_rois: Union[Dict[str, Any], Sequence[Dict[str, Any]]],
        parent_roi: Optional[Sequence[int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        return crop_sub_rois(frame, template_or_sub_rois, parent_roi=parent_roi)

    def validate(self, template_data: Any, raise_on_error: bool = False) -> Tuple[bool, List[str]]:
        return validate_template(template_data, raise_on_error=raise_on_error)
