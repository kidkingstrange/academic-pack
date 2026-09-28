import urllib.request
import json

def test():
    # 1. Article page verification
    req_art = urllib.request.urlopen('http://localhost:8080/blog/academics/100-level-university-academic-transition')
    content_art = req_art.read().decode('utf-8', errors='ignore')
    print('Article page status:', req_art.status)
    print('  Has community section:', 'blog-community-section' in content_art)
    print('  Has comments list:', 'comments-list' in content_art)
    print('  Has topics list:', 'topics-list' in content_art)
    print('  Has community script:', 'blog-community.js' in content_art)

    # 2. Hub page verification
    req_hub = urllib.request.urlopen('http://localhost:8080/blog/')
    content_hub = req_hub.read().decode('utf-8', errors='ignore')
    print('Hub page status:', req_hub.status)
    print('  Has community topics section:', 'community-topics' in content_hub)
    print('  Has community script:', 'blog-community.js' in content_hub)

    # 3. Test API comment submission
    post_comment = json.dumps({
        'slug': '100-level-university-academic-transition',
        'article_title': '100 Level University Academic Transition',
        'what_liked': 'Realistic Advice for Freshers',
        'content': 'This guide made me realize that failing my first MAT 101 quiz is not the end of the world. Great breakdown!',
        'email': 'fresher.student@unilag.edu.ng',
        'name': 'Kelechi A.',
        'school': 'UNILAG'
    }).encode('utf-8')
    comm_req = urllib.request.Request('http://localhost:8080/api/blog/comments', data=post_comment, headers={'Content-Type': 'application/json'}, method='POST')
    comm_res = urllib.request.urlopen(comm_req)
    print('Post comment response:', comm_res.status, json.loads(comm_res.read())['success'])

    # 4. Test API topic submission
    post_topic = json.dumps({
        'title': 'How to study when hostel light is off for 3 days straight',
        'category': 'Hostel & Accommodation',
        'why_needed': 'Power supply is very bad on campus; we need low-power study tactics.',
        'email': 'kelechi@unilag.edu.ng',
        'name': 'Kelechi A.'
    }).encode('utf-8')
    top_req = urllib.request.Request('http://localhost:8080/api/blog/topics', data=post_topic, headers={'Content-Type': 'application/json'}, method='POST')
    top_res = urllib.request.urlopen(top_req)
    print('Post topic response:', top_res.status, json.loads(top_res.read())['success'])

if __name__ == '__main__':
    test()
