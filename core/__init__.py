"""
LabVision Core Subsystems
=========================
Foundational processing, hardware detection, calibration, template engine, and update modules.
"""

from core.updater import GitHubUpdater
from core.template_engine import (
    TemplateEngine,
    LabVisionTemplateError,
    TemplateNotFoundError,
    TemplateCorruptError,
    TemplateValidationError,
    validate_template,
    list_presets,
    list_custom,
    list_all_templates,
    load_template,
    save_template,
    import_template,
    export_template,
    crop_sub_rois,
)

__all__ = [
    "GitHubUpdater",
    "TemplateEngine",
    "LabVisionTemplateError",
    "TemplateNotFoundError",
    "TemplateCorruptError",
    "TemplateValidationError",
    "validate_template",
    "list_presets",
    "list_custom",
    "list_all_templates",
    "load_template",
    "save_template",
    "import_template",
    "export_template",
    "crop_sub_rois",
]
