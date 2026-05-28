"""
Validação estrutural de datasets CSV.
"""

REQUIRED_COLUMNS = (
    "title",
    "language",
    "created_at",
)

OPTIONAL_COLUMNS = (
    "author_association",
    "body",
    "commit_id",
    "diff_hunk",
    "html_url",
    "id",
    "line",
    "path",
    "user",
)


def validate_dataset_columns(
    columns,
):
    """
    Valida colunas obrigatórias do dataset.
    """

    missing_required = tuple(
        column for column in REQUIRED_COLUMNS if column not in columns
    )

    missing_optional = tuple(
        column for column in OPTIONAL_COLUMNS if column not in columns
    )

    return {
        "is_valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }
