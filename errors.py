from flask import redirect, url_for

ERRORS = {
    "unknown": {
        "title": "Something went wrong",
        "message": "An unexpected error occurred. Please try again.",
        "hint": "If the problem persists, check your connection and try later.",
        "back_endpoint": "index",
        "back_label": "Go to home",
    },
    "index_db_error": {
        "title": "Could not load models",
        "message": "The application could not connect to the database or load registered models.",
        "back_endpoint": "index",
        "back_label": "Try again",
    },
    "test_invalid_comparison": {
        "title": "Invalid model selection",
        "message": "No valid model comparison was selected.",
        "hint": "Choose a model from the dropdown before running a prediction.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_model_not_found": {
        "title": "Model not found",
        "message": "The selected model comparison does not exist in the database.",
        "hint": "It may have been removed. Pick another model or register a new one.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_db_error": {
        "title": "Could not load model",
        "message": "A database error occurred while loading the selected model coefficients.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_no_file": {
        "title": "No file uploaded",
        "message": "You must upload a CSV file with gene expression data.",
        "hint": "Select a .csv file containing Gene and Expression columns.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_invalid_file": {
        "title": "Invalid file type",
        "message": "The uploaded file must be a CSV (.csv).",
        "hint": "Export your expression data as a comma-separated file and try again.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_csv_encoding": {
        "title": "Could not read CSV",
        "message": "The CSV file could not be decoded. It may use an unsupported text encoding.",
        "hint": "Save the file as UTF-8 encoded CSV and upload it again.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_csv_columns": {
        "title": "Missing CSV columns",
        "message": 'The CSV file must include "Gene" and "Expression" column headers.',
        "hint": "Check that the first row contains exactly those column names.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_csv_expression": {
        "title": "Invalid expression values",
        "message": "One or more Expression values in the CSV are not valid numbers.",
        "hint": "Ensure every Expression cell contains a numeric value (e.g. 1.23, -0.5).",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "test_csv_invalid": {
        "title": "Could not parse CSV",
        "message": "The CSV file could not be processed.",
        "hint": "Confirm the file is a valid comma-separated table with Gene and Expression columns.",
        "back_endpoint": "test_page",
        "back_label": "Back to test",
    },
    "model_invalid_fields": {
        "title": "Invalid form fields",
        "message": "Both disease names and a model name are required, and the two diseases must be different.",
        "hint": "Use distinct names for each disease class and provide a unique model name.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_duplicate": {
        "title": "Model already exists",
        "message": "A model with this name already exists for the selected disease pair.",
        "hint": "Choose a different model name or disease combination.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_db_error": {
        "title": "Database validation failed",
        "message": "A database error occurred while checking disease names.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_no_file": {
        "title": "No file uploaded",
        "message": "You must upload an RData file containing the trained model.",
        "hint": "Select a .RData or .rda file from your glmnet or caret training output.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_invalid_file": {
        "title": "Invalid file type",
        "message": "The uploaded file must be an RData file (.RData, .rda, or .rdata).",
        "hint": "Upload the RData object saved from your R training script.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_rdata_error": {
        "title": "RData processing failed",
        "message": "The RData file could not be processed by the R training script.",
        "hint": "Ensure the file contains a valid model object.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_rdata_invalid": {
        "title": "Invalid model output",
        "message": "The R script did not return valid gene coefficients.",
        "hint": "Check that the RData file contains one column per gene and vice-versa, and that each row represents a patient.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
    "model_db_save_error": {
        "title": "Could not save model",
        "message": "The model was processed but could not be saved to the database.",
        "hint": "Another user may have registered the same model at the same time.",
        "back_endpoint": "model_page",
        "back_label": "Back to model registration",
    },
}


def get_error(code):
    return ERRORS.get(code, ERRORS["unknown"])


def error_redirect(code):
    return redirect(url_for("error_page", code=code))
