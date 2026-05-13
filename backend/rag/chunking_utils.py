import tiktoken

def count_tokens(text: str, encoding_name: str = "gpt2") -> int:
    """Counts the number of tokens in a given text using the specified encoding."""
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    return len(tokens)


def gpu_memory_available() -> bool:
    """Checks if GPU memory is available."""
    try:
        import torch
        return torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory > 0
    except ImportError:
        return False