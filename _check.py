import re, glob

for f in glob.glob('**/*.html', recursive=True):
    content = open(f, encoding='utf-8').read()
    issues = []
    # nested pre inside code-block
    if '<div class="code-block"><pre>' in content:
        issues.append('pre inside code-block')
    # missing css ref
    if f == 'index.html':
        if 'href="style.css"' not in content:
            issues.append('missing css')
    else:
        if 'href="../style.css"' not in content:
            issues.append('missing css')
    # unclosed tags
    for tag in ['div','section','main','nav','footer','header']:
        opens = len(re.findall(r'<'+tag+r'[>\s]', content))
        closes = len(re.findall(r'</'+tag+r'>', content))
        if opens != closes:
            issues.append(f'{tag}: {opens} open vs {closes} close')
    # duplicate commands in commands.html
    if f == 'docs\\commands.html':
        count = content.count('sli jump-list')
        if count > 1:
            issues.append(f'{count}x sli jump-list (duplicate)')
    if issues:
        print(f'{f}: {issues}')
    else:
        print(f'{f}: OK')
