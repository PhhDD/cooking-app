import os

from google import genai

from cooking_app.ai.schemas import ExtractedRecipe
from cooking_app.ai.youtube_metadata import YouTubeVideoMetadata


class GeminiExtractionError(RuntimeError):
    """Raised when Gemini cannot extract a valid recipe."""


class GeminiRecipeProvider:
    def __init__(
        self,
        client: genai.Client | None = None,
        model: str | None = None,
    ):
        api_key = os.getenv("GEMINI_API_KEY")

        if client is None and not api_key:
            raise GeminiExtractionError(
                "GEMINI_API_KEY is not configured",
            )

        self.client = client or genai.Client(api_key=api_key)
        self.model = model or os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )

    def extract_recipe(
        self,
        metadata: YouTubeVideoMetadata,
    ) -> ExtractedRecipe:
        prompt = f"""
Extract a recipe from the following YouTube video metadata.

Rules:
- Return only information supported by the title and description.
- Do not invent ingredients, quantities, timings, servings, or steps.
- Convert cook time to minutes.
- Use the exact source URL provided.
- If the description does not contain enough recipe information,
  return the best-supported structured result and do not hallucinate.

Video title:
{metadata.title}

Video description:
{metadata.description}

Channel:
{metadata.channel_title}

Source URL:
{metadata.source_url}
""".strip()

        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": ExtractedRecipe.model_json_schema(),
                },
                timeout=60,
            )

            if not interaction.output_text:
                raise GeminiExtractionError(
                    "Gemini returned an empty response",
                )

            recipe = ExtractedRecipe.model_validate_json(
                interaction.output_text,
            )

            if str(recipe.source_url) != metadata.source_url:
                raise GeminiExtractionError(
                    "Gemini returned an unexpected source URL",
                )

            return recipe

        except GeminiExtractionError:
            raise
        except Exception as error:
            raise GeminiExtractionError(
                f"Gemini recipe extraction failed: {error}",
            ) from error
