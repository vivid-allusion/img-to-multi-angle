"""Batch request builder for multi-angle processing operations."""

from typing import Dict, Any, List
from loguru import logger
from .api_client import build_system_prompt
from .payload_builder import build_user_content

MAX_CUSTOM_ID_LENGTH = 64


class BatchRequestBuilder:
    """Builds batch requests from MD items with multiple angles."""

    def __init__(self, config: Dict[str, Any], use_cache: bool = False):
        """Initialize the batch request builder.

        Args:
            config: Configuration dictionary with model settings
            use_cache: Whether to mark system prompt with cache_control
        """
        self.config = config
        self.use_cache = use_cache
        self.system_prompt = build_system_prompt(config)

    def create_batch_requests(
        self, md_items: List[Dict[str, Any]], angles: Dict[str, str], um_template: str
    ) -> List[Dict[str, Any]]:
        """Convert MD items + angles to batch request format.

        Each MD item generates one request per checked angle.

        Args:
            md_items: List of dicts with 'filename', 'dataset_a', 'dataset_b', 'dataset_c', 'checked_angles'
            angles: Dict mapping angle_name -> template content
            um_template: User message template string

        Returns:
            List of batch request objects
        """
        from .user_message_template import render_user_message

        requests = []

        for item in md_items:
            try:
                checked = item.get("checked_angles", list(angles.keys()))
                if not checked:
                    logger.info(f"Skipping {item['filename']}: no angles selected")
                    continue

                for angle_name in checked:
                    if angle_name not in angles:
                        logger.error(f"Angle '{angle_name}' not found in templates for {item['filename']}")
                        continue

                    angle_text = angles[angle_name]
                    user_msg = render_user_message(
                        um_template, item["dataset_b"], item["dataset_c"], angle_text
                    )
                    user_content = build_user_content(
                        scene=item["dataset_a"],
                        original_image=item["dataset_b"],
                        ref_images=item["dataset_c"],
                        angle_text=user_msg,
                    )

                    request = self._build_single_request(
                        item["filename"], angle_name, self.system_prompt, user_content
                    )
                    if request:
                        requests.append(request)

            except Exception as e:
                logger.error(f"Error creating batch requests for {item.get('filename')}: {e}")
                continue

        total_checked = sum(len(item.get("checked_angles", list(angles.keys()))) for item in md_items)
        logger.info(f"Created {len(requests)} batch requests from {len(md_items)} files x {total_checked} checked angles")

        return requests

    def _build_single_request(
        self, filename: str, angle_name: str, system_prompt: str, user_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build a single batch request.

        Args:
            filename: Original filename
            angle_name: Angle template name
            system_prompt: System prompt (scene lives in the user message)
            user_content: Ordered content parts from build_user_content

        Returns:
            Batch request object
        """
        custom_id = self._create_custom_id(filename, angle_name)

        if self.use_cache:
            system_param = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_param = system_prompt

        return {
            "custom_id": custom_id,
            "params": {
                "model": self.config["model"],
                "max_tokens": self.config["max_tokens"],
                "temperature": self.config["temperature"],
                "messages": [{"role": "user", "content": user_content}],
                "system": system_param,
            },
        }

    def _create_custom_id(self, filename: str, angle_name: str) -> str:
        """Create a valid custom_id from filename and angle name.

        Args:
            filename: Original filename
            angle_name: Angle template name

        Returns:
            Valid custom_id
        """
        safe_filename = "".join(c if c.isalnum() or c in "-_" else "_" for c in filename)
        safe_angle = "".join(c if c.isalnum() or c in "-_" else "_" for c in angle_name)
        return f"md_{safe_filename}_{safe_angle}"[:MAX_CUSTOM_ID_LENGTH]
