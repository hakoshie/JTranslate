from jtranslate_app.display_wrap import wrap_display_text

def measure(text):
    return sum(2 if ord(c)>127 else 1 for c in text)

def test_mixed_prose_uses_space_after_english_instead_of_forcing_first_word_alone():
    source='ChatGPT Spaceとは何か。それが今回のテーマです。'
    lines=wrap_display_text(source,measure,26).splitlines()
    assert lines[0].startswith('ChatGPT Spaceとは')
    assert all(measure(line)<=26 for line in lines)

def test_english_words_that_fit_remain_whole():
    lines=wrap_display_text('日本語 translation example 日本語',measure,18).splitlines()
    assert any('translation' in line for line in lines)
    assert any('example' in line for line in lines)

def test_explicit_paragraphs_lists_indentation_and_code_are_preserved():
    source='見出し\n\n- ChatGPT Space\n  code = 123\n```\nprint("hello")\n```'
    assert wrap_display_text(source,measure,80)==source

def test_long_word_and_url_can_emergency_wrap_without_losing_characters():
    for source in ['Supercalifragilisticexpialidocious','https://example.com/very/long/path?q=123456789']:
        lines=wrap_display_text(source,measure,12).splitlines()
        assert ''.join(lines)==source
        assert all(measure(line)<=12 for line in lines)

def test_japanese_punctuation_does_not_start_or_end_wrong_line():
    lines=wrap_display_text('これは「日本語」です。次の文を、確認します。',measure,14).splitlines()
    assert all(not line.startswith(tuple('、。）」』')) for line in lines)
    assert all(not line.endswith(tuple('（「『')) for line in lines)

def test_combining_and_emoji_clusters_are_not_split():
    lines=wrap_display_text('Cafe\u0301 👩\u200d💻 日本語',lambda text:len(text),6).splitlines()
    assert all(not line.startswith('\u0301') and not line.startswith('\u200d') for line in lines)
    assert any('👩\u200d💻' in line for line in lines)
