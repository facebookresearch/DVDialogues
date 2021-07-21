


def get_question_type(template, prior_template):
    last_node_type = template['nodes'][-1]['type']
    text = template['text'][0].lower()
    if 'same set of activities' in text:
        qtype = 'compare action set'
    elif 'same sequence of activities' in text:
        qtype = 'compare action sequence'
    elif 'frequently' in text:
        qtype = 'compare int'
    elif 'how many times' in text:
        qtype = 'action count'
    elif 'how many' in text or 'what number' in text:
        qtype = 'obj count'
    elif 'is there' in text:
        qtype = 'obj exist'
    elif 'what color' in text or 'what material' in text or 'what shape' in text or 'what size' in text:
        qtype = 'attr query'
    elif 'what type of action' in text or 'what is the' in text or 'what types of action' in text:
        qtype = 'action query'
    else:
        assert 'what about' in text
        qtype = get_question_type(prior_template, None)
    return qtype

def get_question_subtype(template, prior_template):
    last_node_type = template['nodes'][-1]['type']
    text = template['text'][0].lower()
    if 'same set of activities' in text:
        if 'how many' in text:
            qtype = 'compare action set (count)'
        else:
            qtype = 'compare action set (exist)'
    elif 'same sequence of activities' in text:
        if 'how many' in text:
            qtype = 'compare action seq (count)'
        else:
            qtype = 'compare action seq (exist)'
    elif 'frequently' in text:
        if 'as frequently' in text:
            qtype = 'compare int (equal)'
        elif 'less frequently' in text:
            qtype = 'compare int (less)'
        elif 'more frequently' in text:
            qtype = 'compare int (more)'
    elif 'how many times' in text:
        qtype = 'action count'
    elif 'how many' in text or 'what number' in text:
        qtype = 'obj count'
    elif 'is there' in text:
        qtype = 'obj exist'
    elif 'what color' in text or 'what about its color' in text:
        qtype = 'attr query (color)'
    elif 'what material' in text or 'what about its material'in text:
        qtype = 'attr query (material)'
    elif 'what shape' in text or 'what about its shape' in text:
        qtype = 'attr query (shape)'
    elif 'what size' in text or 'what about its size' in text:
        qtype = 'attr query (size)'
    elif 'what type of action' in text or 'what is the' in text or 'what types of action' in text:
        if '<o>' in text:
            qtype = 'action query (by order)'
        elif '<f>' in text:
            qtype = 'ation query (by freq)'
        else:
            qtype = 'action query (all actions)'
    else:
        assert 'what about' in text
        assert 'color' not in text and 'size' not in text and \
                'shape' not in text and 'material' not in text
        qtype = get_question_subtype(prior_template, None)
    return qtype