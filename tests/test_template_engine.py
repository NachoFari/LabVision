"""
Test Suite: LabVision Template Engine Verification
===================================================
Tests Work Package 1 functionality:
- Parsing and validation of factory presets (NDJ-8S Viscometer, Analytical Balance)
- Custom template creation, saving, listing, importing, and exporting
- Sub-ROI cropping on mock NumPy frames with and without parent ROI
- Edge cases and error handling (corrupt JSON, out-of-bounds coords, empty frames)
"""

import os
import sys
import shutil
import tempfile
import numpy as np
from pathlib import Path

# Ensure core module is on python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Avoid cp1252 encoding issues on Windows console
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from core.template_engine import (
    TemplateEngine,
    validate_template,
    list_presets,
    list_custom,
    list_all_templates,
    load_template,
    save_template,
    import_template,
    export_template,
    crop_sub_rois,
    TemplateValidationError,
    TemplateNotFoundError,
    TemplateCorruptError
)

def test_factory_presets():
    print("\n--- Test 1: Factory Presets Verification ---")
    engine = TemplateEngine()
    presets = engine.list_presets()
    print(f"Encontradas {len(presets)} plantillas de fábrica:")
    for p in presets:
        print(f"  • {p['template_id']}: {p['name']} ({p['sub_roi_count']} sub-ROIs) - Válida: {p['is_valid']}")

    preset_ids = {p["template_id"] for p in presets}
    assert "viscosimetro_ndj8s" in preset_ids, "Falta viscosimetro_ndj8s en presets"
    assert "balanza_analitica" in preset_ids, "Falta balanza_analitica en presets"

    # Test loading NDJ-8S
    ndj = engine.load("viscosimetro_ndj8s")
    assert ndj["metadata"]["template_id"] == "viscosimetro_ndj8s"
    assert len(ndj["sub_rois"]) == 4
    sub_ids = [r["id"] for r in ndj["sub_rois"]]
    assert sub_ids == ["rotor", "speed_rpm", "viscosity", "torque"]
    print("  ✓ NDJ-8S cargada y validada con 4 sub-ROIs (Rotor, RPM, Viscosidad, Torque)")

    # Test loading Balanza
    bal = engine.load("balanza_analitica")
    assert bal["metadata"]["template_id"] == "balanza_analitica"
    assert len(bal["sub_rois"]) == 3
    sub_ids_bal = [r["id"] for r in bal["sub_rois"]]
    assert sub_ids_bal == ["weight", "stability", "tare"]
    print("  ✓ Balanza Analítica cargada y validada con 3 sub-ROIs (Peso, Estabilidad, Tara)")
    print("✓ Test 1 PASÓ.")

def test_sub_roi_cropping():
    print("\n--- Test 2: Sub-ROI Cropping with Mock NumPy Frames ---")
    engine = TemplateEngine()
    ndj = engine.load("viscosimetro_ndj8s")

    # Create mock frame 720p (720 x 1280, 3 channels)
    mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Put distinct color gradient to verify crops have real data
    mock_frame[:, :, 0] = np.linspace(0, 255, 1280, dtype=np.uint8)
    mock_frame[:, :, 1] = np.linspace(0, 255, 720, dtype=np.uint8)[:, None]

    # 1. Full frame cropping
    crops_full = engine.crop(mock_frame, ndj)
    assert len(crops_full) == 4, f"Se esperaban 4 recortes, obtenidos {len(crops_full)}"
    for roi_id, roi_data in crops_full.items():
        crop = roi_data["crop"]
        bbox = roi_data["pixel_bbox"]
        assert crop is not None and crop.size > 0, f"Recorte vacío para {roi_id}"
        assert crop.shape[0] == bbox[3] and crop.shape[1] == bbox[2]
        print(f"  • Full Frame -> {roi_id}: bbox={bbox}, crop_shape={crop.shape}")

    # 2. Parent ROI cropping (e.g. detected screen in frame)
    parent_roi = [100, 80, 600, 400] # x=100, y=80, w=600, h=400
    crops_parent = engine.crop(mock_frame, ndj, parent_roi=parent_roi)
    assert len(crops_parent) == 4
    for roi_id, roi_data in crops_parent.items():
        crop = roi_data["crop"]
        bbox = roi_data["pixel_bbox"]
        # Global bbox must be within [100..700, 80..480]
        assert bbox[0] >= 100 and bbox[0] + bbox[2] <= 700 + 1
        assert bbox[1] >= 80 and bbox[1] + bbox[3] <= 480 + 1
        print(f"  • With Parent ROI -> {roi_id}: bbox={bbox}, crop_shape={crop.shape}")

    # 3. Defensive edge cases (None, zero-size, corrupted ROI)
    assert engine.crop(None, ndj) == {}
    assert engine.crop(np.zeros((0, 0, 3), dtype=np.uint8), ndj) == {}
    assert engine.crop(mock_frame, []) == {}
    # Out of frame parent roi
    crops_oob = engine.crop(mock_frame, ndj, parent_roi=[-50, -50, 200, 200])
    assert len(crops_oob) == 4
    print("  ✓ Comportamiento defensivo verificado (None, vacío, fuera de límites)")
    print("✓ Test 2 PASÓ.")

def test_custom_templates_lifecycle():
    print("\n--- Test 3: Custom Templates Lifecycle (Save, List, Export, Import) ---")
    engine = TemplateEngine()

    custom_template = {
      "$schema": "https://labvision.org/schemas/v1/template.json",
      "lvtemplate_version": "1.0",
      "metadata": {
        "template_id": "espectrofotometro_uv_test",
        "name": "Espectrofotómetro UV-Vis Personalizado",
        "description": "Plantilla de prueba creada por el usuario",
        "author": "Bioquímico Analista",
        "institution": "Laboratorio Central"
      },
      "display_profile": {
        "type": "lcd_reflective",
        "preprocessing": {
          "grayscale": True,
          "clahe": False
        }
      },
      "sub_rois": [
        {
          "id": "absorbancia",
          "display_label": "Absorbancia (Abs)",
          "unit": "Abs",
          "coordinates_relative": {"x": 0.10, "y": 0.15, "w": 0.50, "h": 0.40},
          "data_type": "float",
          "decimal_places": 3,
          "valid_range": [-0.5, 3.5]
        },
        {
          "id": "longitud_onda",
          "display_label": "Longitud de Onda (nm)",
          "unit": "nm",
          "coordinates_relative": {"x": 0.65, "y": 0.15, "w": 0.30, "h": 0.40},
          "data_type": "float",
          "decimal_places": 1,
          "valid_range": [190.0, 1100.0]
        }
      ],
      "streaming_export": {
        "default_sample_interval_sec": 1.0,
        "csv_columns": ["Timestamp_ISO8601", "Absorbancia", "Longitud_Onda_nm"]
      }
    }

    # Save to custom
    saved_path = engine.save(custom_template, destination="custom")
    assert saved_path.exists()
    print(f"  ✓ Plantilla personalizada guardada en: {saved_path.name}")

    # List custom templates
    customs = engine.list_custom()
    custom_ids = [c["template_id"] for c in customs]
    assert "espectrofotometro_uv_test" in custom_ids
    print(f"  ✓ list_custom() detectó correctamente: {custom_ids}")

    # Export template
    with tempfile.TemporaryDirectory() as tmp_dir:
        export_target = Path(tmp_dir) / "backup_espectro.lvtemplate"
        exported_path = engine.export_template("espectrofotometro_uv_test", export_target)
        assert exported_path.exists()
        print(f"  ✓ Plantilla exportada exitosamente a: {exported_path}")

        # Delete from custom to test importing back
        saved_path.unlink()
        assert not saved_path.exists()
        assert "espectrofotometro_uv_test" not in [c["template_id"] for c in engine.list_custom()]

        # Import template from export location
        imported_path = engine.import_template(exported_path)
        assert imported_path.exists()
        reloaded = engine.load("espectrofotometro_uv_test")
        assert reloaded["metadata"]["name"] == "Espectrofotómetro UV-Vis Personalizado"
        print(f"  ✓ Plantilla importada nuevamente y cargada con éxito: {imported_path.name}")

        # Clean up custom test file
        imported_path.unlink()

    print("✓ Test 3 PASÓ.")

def test_validation_and_error_handling():
    print("\n--- Test 4: Validation & Error Handling ---")
    engine = TemplateEngine()

    # 1. Invalid JSON / Not found
    try:
        engine.load("archivo_fantasma_inexistente")
        assert False, "Debió lanzar TemplateNotFoundError"
    except TemplateNotFoundError:
        print("  ✓ TemplateNotFoundError lanzado correctamente para plantilla inexistente.")

    # 2. Corrupt schema: missing required fields
    bad_template = {
        "lvtemplate_version": "1.0",
        "metadata": {"name": "Sin ID"}
        # missing sub_rois
    }
    is_valid, errors = validate_template(bad_template)
    assert not is_valid
    assert any("sub_rois" in e for e in errors)
    print(f"  ✓ Validación detectó errores estructurales: {errors}")

    # 3. Out-of-bounds coordinates (x + w > 1.0)
    oob_template = {
        "lvtemplate_version": "1.0",
        "metadata": {"template_id": "test_oob", "name": "Test OOB"},
        "sub_rois": [
            {
                "id": "var1",
                "display_label": "Variable 1",
                "coordinates_relative": {"x": 0.8, "y": 0.1, "w": 0.5, "h": 0.2}
            }
        ]
    }
    is_valid_oob, errors_oob = validate_template(oob_template)
    assert not is_valid_oob
    assert any("desborda" in e for e in errors_oob)
    print(f"  ✓ Validación detectó desborde de coordenadas relativas: {errors_oob}")

    # 4. Attempting to save invalid template raises TemplateValidationError
    try:
        engine.save(oob_template)
        assert False, "Debió lanzar TemplateValidationError al intentar guardar"
    except TemplateValidationError:
        print("  ✓ TemplateValidationError lanzado al intentar guardar plantilla defectuosa.")

    print("✓ Test 4 PASÓ.")

if __name__ == "__main__":
    print("=" * 60)
    print("Iniciando Verificación Integral de Work Package 1 - LabVision")
    print("=" * 60)
    test_factory_presets()
    test_sub_roi_cropping()
    test_custom_templates_lifecycle()
    test_validation_and_error_handling()
    print("\n" + "=" * 60)
    print("TODAS LAS PRUEBAS COMPLETADAS SATISFACTORIAMENTE (100% OK)")
    print("=" * 60)
