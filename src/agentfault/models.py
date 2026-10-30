from typing import Any, Literal

from pydantic import BaseModel, model_validator


class ToolResult(BaseModel):
    """Standard response returned by a simulated business tool."""

    status: Literal["success", "failure"]
    data: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None

    @model_validator(mode="after")
    def validate_response(self):
        if self.status == "success":
            if self.data is None:
                raise ValueError(
                    "Successful results must contain data"
                )

            if self.error is not None or self.error_type is not None:
                raise ValueError(
                    "Successful results cannot contain errors"
                )

        if self.status == "failure":
            if not self.error:
                raise ValueError(
                    "Failed results must contain an error"
                )

            if self.data is not None:
                raise ValueError(
                    "Failed results cannot contain data"
                )

        return self