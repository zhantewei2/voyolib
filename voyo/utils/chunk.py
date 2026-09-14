"""文本分块工具 — 基于 tiktoken。"""

import re

from voyo.utils.token import estimate_token_count, token_segments

_PUNCT_PATTERN = re.compile(r"[.。；;]")


def chunk_split_paragraph(text: str, token_size: int, max_tokens: int, overlay_token_size: int = 0) -> list[dict]:
    """将文本按 token 大小分块。每个 dict：{"chunk": str (trimmed), "token_size": int}

    overlay_token_size: 每块末尾按段落向下多取的 token 数（冗余），不影响下一块起点；0 则不多取。
    """
    if not text or token_size <= 0:
        return []
    overlay_token_size = min(max(overlay_token_size, 0), token_size)

    segments = token_segments(text)
    n = len(segments)
    result: list[dict] = []
    pos = 0

    while pos < n:
        while pos < n and segments[pos][0] in " \t\n":
            pos += 1
        if pos >= n:
            break

        estimated = pos + token_size

        if estimated >= n:
            split_at = n
        else:
            front_nl = next((i for i in range(estimated - 1, pos - 1, -1) if "\n" in segments[i][0]), -1)
            rear_nl = next((i for i in range(estimated, n) if "\n" in segments[i][0]), -1)

            split_at: int

            # 后方更近：缩到 rear_nl（不含）
            if rear_nl != -1 and (front_nl == -1 or (rear_nl - estimated) <= (estimated - front_nl)):
                split_at = rear_nl
            # 前方更近：延伸包含 front_nl 及其前内容
            elif front_nl != -1:
                split_at = front_nl + 1
            else:
                # 无换行：前方 max_tokens 范围内找换行
                fwd_nl = next((i for i in range(estimated, min(estimated + max_tokens, n)) if "\n" in segments[i][0]), -1)
                if fwd_nl != -1:
                    split_at = fwd_nl
                else:
                    # 找标点
                    punct = next((i for i in range(pos, min(pos + max_tokens, n)) if _PUNCT_PATTERN.search(segments[i][0])), -1)
                    split_at = punct + 1 if punct != -1 else min(pos + max_tokens, n)

            if split_at <= pos:
                split_at = pos + 1
            if split_at > n:
                split_at = n

        # overlay：向下按段落整段多取，下一块起点仍为 split_at
        end = split_at
        remaining = overlay_token_size
        i = split_at
        while remaining > 0 and i < n:
            nl = next((j for j in range(i, n) if "\n" in segments[j][0]), -1)
            seg_end = nl + 1 if nl != -1 else n
            if seg_end - i > remaining:
                break
            end = seg_end
            remaining -= seg_end - i
            i = seg_end

        start_char = segments[pos][1]
        end_char = segments[end][1] if end < n else len(text)
        chunk_text = text[start_char:end_char].strip()
        if chunk_text:
            result.append({"chunk": chunk_text, "token_size": estimate_token_count(chunk_text)})

        if end >= n:
            break
        pos = split_at

    return result
