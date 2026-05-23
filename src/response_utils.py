#!/usr/bin/env python3
"""Utility functions for handling OpenRouter API responses."""


def extract_response_text(response) -> str:
    """Extract text content from OpenRouter response.
    
    Args:
        response: OpenRouter API response object
        
    Returns:
        Extracted text content or empty string if not found
    """
    if response.choices and len(response.choices) > 0:
        message = response.choices[0].message
        if hasattr(message, 'content') and message.content:
            return message.content
    return ""
