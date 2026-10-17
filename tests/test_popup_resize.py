from jtranslate_app.popup_geometry import resize_rect
from jtranslate_app.translation import normalize_prose_breaks


def test_resize_corner_and_minimum_keep_opposite_corner():
    assert resize_rect((100,100,500,300),'se',100,80,(0,0,1000,800)) == (100,100,600,380)
    assert resize_rect((100,100,500,300),'nw',1000,1000,(0,0,1000,800)) == (280,300,320,100)


def test_resize_cannot_leave_monitor_work_area():
    assert resize_rect((100,100,500,300),'se',5000,5000,(0,0,1000,800)) == (100,100,900,700)
    assert resize_rect((100,100,500,300),'nw',-5000,-5000,(0,0,1000,800)) == (0,0,600,400)


def test_pdf_soft_lines_join_but_real_structures_survive():
    source='This sentence was wrapped\nacross two PDF lines.\n\nNext paragraph.\n- first item\n- second item\n\n```python\nx = 1\ny = 2\n```'
    expected='This sentence was wrapped across two PDF lines.\n\nNext paragraph.\n- first item\n- second item\n\n```python\nx = 1\ny = 2\n```'
    assert normalize_prose_breaks(source) == expected


def test_japanese_wrap_and_complete_sentences():
    assert normalize_prose_breaks('これは文章の途中\nに入った改行です。\n次の文です。') == 'これは文章の途中に入った改行です。\n次の文です。'
    assert normalize_prose_breaks('Title\n  indented code\n    next line\n\n1. item\n2. item') == 'Title\n  indented code\n    next line\n\n1. item\n2. item'
