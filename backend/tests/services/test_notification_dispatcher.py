import uuid

from app.services.notification_dispatcher import (
    FCM_MAX_PAYLOAD_BYTES,
    _estimate_fcm_payload_size,
    chunk_messages_for_fcm,
)


def _make_message(recipient: str = "+1234567890") -> dict:
    return {"message_id": str(uuid.uuid4()), "recipient": recipient}


def test_estimate_fcm_payload_size():
    messages = [_make_message()]
    body = "Hello"
    size = _estimate_fcm_payload_size(messages, body)
    assert size > 0
    assert isinstance(size, int)


def test_chunk_messages_empty():
    assert chunk_messages_for_fcm([], "Hello") == []


def test_chunk_messages_single_fits():
    messages = [_make_message() for _ in range(5)]
    chunks = chunk_messages_for_fcm(messages, "Hello")
    assert len(chunks) == 1
    assert chunks[0] == messages


def test_chunk_messages_splits_when_exceeding_limit():
    # Generate enough messages to exceed 4KB
    messages = [_make_message() for _ in range(100)]
    body = "Test message body"
    chunks = chunk_messages_for_fcm(messages, body)

    assert len(chunks) > 1

    # Every chunk must fit within the limit
    for chunk in chunks:
        size = _estimate_fcm_payload_size(chunk, body)
        assert size <= FCM_MAX_PAYLOAD_BYTES, (
            f"Chunk with {len(chunk)} messages is {size}B, exceeds {FCM_MAX_PAYLOAD_BYTES}B"
        )

    # All messages must be preserved across chunks
    total = sum(len(c) for c in chunks)
    assert total == len(messages)


def test_chunk_messages_with_long_body():
    body = "A" * 1600  # Max SMS body length
    messages = [_make_message() for _ in range(50)]
    chunks = chunk_messages_for_fcm(messages, body)

    for chunk in chunks:
        size = _estimate_fcm_payload_size(chunk, body)
        assert size <= FCM_MAX_PAYLOAD_BYTES


def test_chunk_messages_preserves_order():
    messages = [_make_message(f"+{i:010d}") for i in range(80)]
    body = "Test"
    chunks = chunk_messages_for_fcm(messages, body)

    flattened = [msg for chunk in chunks for msg in chunk]
    assert flattened == messages


def test_single_message_always_fits():
    """A single message with max body should still produce one chunk."""
    body = "B" * 1600
    messages = [_make_message()]
    chunks = chunk_messages_for_fcm(messages, body)
    assert len(chunks) == 1
    assert chunks[0] == messages
