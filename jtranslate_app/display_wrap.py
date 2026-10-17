"""Display-only Japanese/Latin wrapping; the original result stays unchanged."""
import unicodedata

OPENING = set('（［｛〈《「『【〔〖〘〚([{')
CLOSING = set('、。，．？！：；）］｝〉》」』】〕〗〙〛)]},.!?:;')


def clusters(text):
    """Keep combining marks, variation selectors and common emoji sequences together."""
    result=[]
    regional=0
    for char in text:
        point=ord(char)
        extend=(unicodedata.category(char).startswith('M') or
                0xFE00<=point<=0xFE0F or 0xE0100<=point<=0xE01EF or
                0x1F3FB<=point<=0x1F3FF or char=='\u200d')
        flag=0x1F1E6<=point<=0x1F1FF
        if result and (extend or result[-1].endswith('\u200d') or (flag and regional%2)):
            result[-1]+=char
        else:
            result.append(char)
        regional=regional+1 if flag else 0
    return result


def units(line):
    pieces=[];word=''
    for cluster in clusters(line):
        separate=(cluster.isspace() or cluster[0] in OPENING|CLOSING or
                  unicodedata.east_asian_width(cluster[0]) in 'WF')
        if separate:
            if word:pieces.append(word);word=''
            pieces.append(cluster)
        else:
            word+=cluster
    if word:pieces.append(word)
    result=[];opening=''
    for piece in pieces:
        if piece[0] in OPENING:
            opening+=piece
        elif piece[0] in CLOSING and result and not opening:
            result[-1]+=piece
        else:
            result.append(opening+piece);opening=''
    if opening:result.append(opening)
    return result


def wrap_display_text(source, measure, width):
    """Retain explicit newlines; add visual breaks only at measured boundaries.

    Words that fit the viewport stay whole. Overlong words/URLs use emergency
    grapheme breaks. Tabs expand only for display, never in the copied result.
    """
    width=max(1,width)
    rendered=[]
    for source_line in source.split('\n'):
        line=source_line.expandtabs(8)
        if measure(line)<=width:
            rendered.append(line)
            continue
        current=''
        for unit in units(line):
            if measure(current+unit)<=width:
                current+=unit
            elif measure(unit)<=width:
                if current:rendered.append(current.rstrip())
                current='' if unit.isspace() else unit
            else:
                # No legal whole-word break fits. Keep each grapheme intact.
                for cluster in clusters(unit):
                    if current and measure(current+cluster)>width:
                        rendered.append(current.rstrip());current=''
                    current+=cluster
        rendered.append(current)
    return '\n'.join(rendered)
