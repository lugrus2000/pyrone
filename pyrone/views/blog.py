## -*- coding: utf-8 -*-
import logging
import re
import transaction
import uuid
import os

from PIL import Image
from sqlalchemy.orm import eagerload
from time import time

from pyramid.response import Response
from pyramid.i18n import TranslationString as _
from pyramid.view import view_config
from pyramid.url import route_url
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound, HTTPNotFound, HTTPServerError
from pyramid.renderers import render

from pyrone.models import DBSession, Article, Comment, Tag, File, VerifiedEmail
from pyrone.models.config import get as get_config
from pyrone.lib import helpers as h, auth, markup, notifications
from pyrone.models.file import get_storage_dirs, allowed_dltypes
from pyrone.models.user import normalize_email

log = logging.getLogger(__name__)

@view_config(route_name='blog_latest', renderer='/blog/list_articles.mako')
def latest(request):
    """
    Display list of articles sorted by publishing date ascending,
    show rendered previews, not complete articles
    """
    c = dict(articles=list())
    
    h = []
    for x in request.headers.iteritems():
        h.append('%s: %s' % x )
    log.debug('\n'.join(h))
    
    page_size = int(get_config('elements_on_page'))
    start_page = 0
    if 'start' in request.GET:
        try:
            start_page = int(request.GET['start'])
        except ValueError:
            start_page = 0
    
    dbsession= DBSession()
    user = auth.get_user(request)
    
    q = dbsession.query(Article).options(eagerload('tags')).options(eagerload('user')).order_by(Article.published.desc())
    if not user.has_permission('edit_article'):
        q = q.filter(Article.is_draft==False)
        
    c['articles'] = q[(start_page * page_size) : (start_page+1) * page_size + 1]
    
    for article in c['articles']:
        log.debug(article.shortcut_date)
    
    c['prev_page'] = None
    if len(c['articles']) > page_size:
        c['prev_page'] = route_url('blog_latest', request, _query=[('start', start_page+1)])
        c['articles'].pop()
        
    c['next_page'] = None
    if start_page > 0:
        c['next_page'] = route_url('blog_latest', request, _query=[('start', start_page-1)])
    
    c['page_title'] = _('Latest articles')
    
    return c

@view_config(route_name='blog_tag_articles', renderer='/blog/list_articles.mako')
def tag_articles(request):
    tag = request.matchdict['tag']
    
    page_size = int(get_config('elements_on_page'))
    start_page = 0
    if 'start' in request.GET:
        try:
            start_page = int(request.GET['start'])
        except ValueError:
            start_page = 0
            
    user = auth.get_user(request)
    dbsession= DBSession()
    q = dbsession.query(Article).join(Tag).options(eagerload('tags')).options(eagerload('user')).order_by(Article.published.desc())
    if not user.has_permission('edit_article'):
        q = q.filter(Article.is_draft==False)
    
    c = dict()
    c['articles'] = q.filter(Tag.tag==tag)[(start_page * page_size) : (start_page+1) * page_size + 1]
    
    for article in c['articles']:
        log.debug(article.shortcut_date)
    
    c['prev_page'] = None
    if len(c['articles']) > page_size:
        c['prev_page'] = route_url('blog_latest', request, _query=[('start', start_page+1)])
        c['articles'].pop()
        
    c['next_page'] = None
    if start_page > 0:
        c['next_page'] = route_url('blog_latest', request, _query=[('start', start_page-1)])
    
    c['page_title'] = _(u'Articles labeled with tag “%s”' % tag)
    
    return c
    

def _check_article_fields(article, request):
    """
    Read article from the POST request, also validate data
    """
    errors = dict()
    # check passed data
    fields = ['title', 'shortcut', 'body']
    for f in fields:
        if f in request.POST:
            setattr(article, f, request.POST[f])

    req_fields = ['title', 'shortcut', 'body']
    for f in req_fields:
        if not getattr(article, f):
            errors[f] = _('field is required')

    # optional boolean values
    fields = ['is_draft', 'is_commentable']
    for f in fields:
        if f in request.POST:
            setattr(article, f, True)
        else:
            setattr(article, f, False)

    # render body
    article.set_body(request.POST['body'])
    
    return errors

@view_config(route_name='blog_write_article', renderer='/blog/write_article.mako', permission='write_article')
def write_article(request):
    c = dict(
         new_article=True, 
         submit_url=route_url('blog_write_article', request),
         errors=dict(),
         tags=list() )

    if request.method == 'GET':
        a = Article('new-article-shortcut', 'New article title')
        c['tags'] = []
        c['article'] = a
        c['article_published_str'] = h.timestamp_to_str(a.published)
        
    elif request.method == 'POST':
        article = Article()
        e = _check_article_fields(article, request)
        c['errors'].update(e)
        c['article_published_str'] = request.POST['published']
        
        if 'published' not in request.POST:
            c['errors']['published'] = _('invalid date and time format')
        else:
            # parse value to check structure
            date_re = re.compile('^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2})$')
            mo = date_re.match(request.POST['published'])
            if mo is None:
                c['errors']['published'] = _('invalid date and time format')
            else:
                # we need to convert LOCAL date and time to UTC seconds
                article.published = h.str_to_timestamp(request.POST['published'])
                article.shortcut_date = '%04d/%02d/%02d' % tuple([int(x) for x in mo.groups()[0:3]])
            
            dbsession = DBSession()
            q = dbsession.query(Article).filter(Article.shortcut_date==article.shortcut_date)\
                .filter(Article.shortcut==article.shortcut)
            res = q.first()
    
            if res is not None:
                c['errors']['shortcut'] = _('duplicated shortcut')
        
        # tags
        c['tags'] = []
        if 'tags' in request.POST:
            tags_str = request.POST['tags']
            tags = set([s.strip() for s in tags_str.split(',')])

            for tag_str in tags:
                if tag_str == '':
                    continue
                c['tags'].append(tag_str)
                
        if len(c['errors']) == 0:
            dbsession = DBSession()
            transaction.begin()
            
            # save and redirect
            user = auth.get_user(request)
            article.user_id = user.id
            dbsession.add(article)
            dbsession.flush() # required as we need to obtain article_id
            
            article_id = article.id

            for tag_str in c['tags']:
                tag = Tag(tag_str, article)
                dbsession.add(tag)
                
            transaction.commit()
            
            return HTTPFound(location=route_url('blog_go_article', request, article_id=article_id))
            
        c['article'] = article
            
    else:
        return HTTPBadRequest()
        
    return c

@view_config(route_name='blog_edit_article', renderer='/blog/write_article.mako', permission='write_article')
def edit_article(request):
    article_id = int(request.matchdict['article_id'])
    c = dict()
    c['errors'] = dict()
    c['new_article'] = False
    
    dbsession = DBSession()
    
    if request.method == 'GET':
        article = dbsession.query(Article).get(article_id)
        c['tags'] = [tag.tag for tag in article.tags]
        c['article_published_str'] = h.timestamp_to_str(article.published)
    elif request.method == 'POST':
        transaction.begin()
        article = dbsession.query(Article).get(article_id)
        # check fields etc
        e = _check_article_fields(article, request)
        c['errors'].update(e)
        c['article_published_str'] = request.POST['published']
        
        if 'published' not in request.POST:
            c['errors']['published'] = _('invalid date and time format')
        else:
            # parse value to check structure
            date_re = re.compile('^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2})$')
            mo = date_re.match(request.POST['published'])
            if mo is None:
                c['errors']['published'] = _('invalid date and time format')
            else:
                # we need to convert LOCAL date and time to UTC seconds
                article.published = h.str_to_timestamp(request.POST['published'])
                article.shortcut_date = '%04d/%02d/%02d' % tuple([int(x) for x in mo.groups()[0:3]])
            
            dbsession = DBSession()
            q = dbsession.query(Article).filter(Article.shortcut_date==article.shortcut_date)\
                .filter(Article.id != article_id)\
                .filter(Article.shortcut==article.shortcut)
            res = q.first()
    
            if res is not None:
                c['errors']['shortcut'] = _('duplicated shortcut')
                
        # tags
        c['tags'] = [] # these are new tags
        if 'tags' in request.POST:
            tags_str = request.POST['tags']
            tags = set([s.strip() for s in tags_str.split(',')])

            for tag_str in tags:
                if tag_str == '':
                    continue
                c['tags'].append(tag_str)
                
        if len(c['errors']) == 0:
            for tag in article.tags:
                dbsession.delete(tag)
                
            for tag_str in c['tags']:
                tag = Tag(tag_str, article)
                dbsession.add(tag)
                
            transaction.commit()
            
            return HTTPFound(location=route_url('blog_go_article', request, article_id=article_id))
        else:
            transaction.abort()
        
    else:
        return HTTPBadRequest()
    
    if article is None:
        return HTTPNotFound()
    
    c['article'] = article
    c['submit_url'] = route_url('blog_edit_article', request, article_id=article_id)
    return c

@view_config(route_name='blog_preview_article', permission='write_article')
def preview_article(request):
    preview, complete = markup.render_text_markup(request.POST['body']) #@UnusedVariable
    
    return Response(body=complete, content_type='text/html')

def _view_article(request, article_id=None, article=None):
    c = dict()
    
    dbsession = DBSession()
    
    if article is None:
        article = dbsession.query(Article).get(article_id)
        
    if article is None:
        return HTTPNotFound()
    
    comments = dbsession.query(Comment).filter(Comment.article==article).all()
    comments_dict = dict()
    
    for x in comments:
        if x.parent_id not in comments_dict:
            comments_dict[x.parent_id] = list()
        if x.user is not None:
            x._real_email = x.user.email
        else:
            x._real_email = x.email
        if x._real_email == '':
            x._real_email = None
        comments_dict[x.parent_id].append(x)

    scope = dict(thread=[])

    def build_thread(parent_id, indent):
        if parent_id not in comments_dict:
            return

        for x in comments_dict[parent_id]:
            setattr(x, '_indent', indent)
            scope['thread'].append(x)
            build_thread(x.id, indent+1)

    build_thread(None, 0)
    c['comments'] = scope['thread']
    
    signature = str(uuid.uuid4()).replace('-', '')
    is_subscribed = False
    
    for cn in ('comment_display_name', 'comment_email', 'comment_website'):
        if cn in request.cookies:
            c[cn] = request.cookies[cn]
        else:
            c[cn] = ''
            
    if 'is_subscribed' in request.cookies and request.cookies['is_subscribed'] == 'true':
        is_subscribed = True
    
    c['article'] = article
    c['signature'] = signature
    c['is_subscribed'] = is_subscribed
    
    return c

@view_config(route_name='blog_go_article', renderer='/blog/view_article.mako')
def go_article(request):
    article_id = int(request.matchdict['article_id'])
    
    return _view_article(request, article_id=article_id)

@view_config(route_name='blog_view_article', renderer='/blog/view_article.mako')
def view_article(request):
    shortcut_date = request.matchdict['shortcut_date']
    shortcut = request.matchdict['shortcut']
    
    dbsession = DBSession()
    q = dbsession.query(Article).filter(Article.shortcut_date==shortcut_date).filter(Article.shortcut==shortcut)
    user = auth.get_user(request)
    if not user.has_permission('edit_article'):
        q = q.filter(Article.is_draft==False)
    article = q.first()
    
    if 'commentid' in request.GET:
        # redirect to comment URL, this trick is required because some 
        # browsers don't reload page after changing page anchor (e.g. http://example.com/index#abc)
        comment_url = h.article_url(request, article) + '#comment-' + request.GET['commentid']
        return HTTPFound(location=comment_url)

    return _view_article(request, article=article)

@view_config(route_name='blog_add_article_comment_ajax', renderer='json', request_method='POST')
def add_article_comment_ajax(request):
    article_id = int(request.matchdict['article_id'])
    
    dbsession = DBSession()
    transaction.begin()
    
    q = dbsession.query(Article).filter(Article.id==article_id)
    user = auth.get_user(request)
    if not user.has_permission('edit_article') or not user.has_permission('admin'):
        q = q.filter(Article.is_draft==False)
    article = q.first()
    
    if article is None or not article.is_commentable:
        transaction.abort()
        return HTTPNotFound()
    
    if 's' not in request.POST:
        transaction.abort()
        return HTTPBadRequest()
    
    json = dict()
    
    key = request.POST['s']

    # all data elements are constructed from the string "key" as substrings
    body_ind = key[3:14]
    parent_ind = key[4:12]
    display_name_ind = key[0:5]
    email_ind = key[13:25]
    website_ind = key[15:21]
    is_subscribed_ind = key[19:27]
    
    for ind in (body_ind, parent_ind, display_name_ind, email_ind, website_ind):
        if ind not in request.POST:
            transaction.abort()
            return HTTPBadRequest()
        
    body = request.POST[body_ind]
        
    if len(body) == 0:
        transaction.abort()
        return dict(error=_('Empty comment body is not allowed.'))
    
    comment = Comment()
    comment.set_body(body)
    
    user = auth.get_user(request)
    
    if user.kind != 'anonymous':
        comment.user_id = user.id
    else:
        # get "email", "display_name" and "website" arguments
        comment.display_name = request.POST[display_name_ind]
        comment.email = request.POST[email_ind]
        comment.website = request.POST[website_ind]
        
        # remember email, display_name and website in browser cookies
        request.response.set_cookie('comment_display_name', comment.display_name, max_age=31536000)
        request.response.set_cookie('comment_email', comment.email, max_age=31536000)
        request.response.set_cookie('comment_website', comment.website, max_age=31536000)
        
    # set parent comment
    parent_id = request.POST[parent_ind]
    try:
        parent_id = int(parent_id)
    except ValueError:
        parent_id = None

    if parent_id:
        parent = dbsession.query(Comment).filter(Comment.id==parent_id).filter(Comment.article_id==article_id).first()
        if parent is not None:
            if not parent.is_approved:
                #
                transaction.abort()
                data = dict(error=_('Answering to not approved comment'))
                return json.dumps(data)
            
    comment.parent_id = parent_id
    comment.article_id = article_id
    
    if is_subscribed_ind in request.POST:
        comment.is_subscribed = True
    
    # this list contains notifications    
    ns = list()
    
    # if user has subscribed to answer then check is his/her email verified
    # if doesn't send verification message to the email
    if is_subscribed_ind in request.POST:
        vrf_email = ''
        if user.kind != 'anonymous':
            vrf_email = user.email
        elif request.POST[email_ind]:
            vrf_email = request.POST[email_ind]
            
        vrf_email = normalize_email(vrf_email)
        if vrf_email:
            # email looks ok so proceed
            
            send_evn = False
        
            vf = dbsession.query(VerifiedEmail).filter(VerifiedEmail.email==vrf_email).first()
            vf_token = ''
            if vf is not None:
                if not vf.is_verified:
                    diff = time() - vf.last_verify_date
                    #if diff > 86400:
                    if diff > 1:
                        # delay between verifications requests must be more than 24 hours
                        send_evn = True
                    vf.last_verify_date = time()
                    vf_token = vf.verification_code
                
            else:
                send_evn = True
                vf = VerifiedEmail(vrf_email)
                vf_token = vf.verification_code
                dbsession.add(vf)
            
            if send_evn:
                ns.append(notifications.gen_email_verification_notification(vrf_email, vf_token))

    request.response.set_cookie('is_subscribed', 'true' if comment.is_subscribed else 'false', max_age=31536000)

    # automatically approve comment if user has permission "admin", "write_article" or "edit_article"
    if user.has_permission('admin') or user.has_permission('write_article') \
            or user.has_permission('edit_article'):
        comment.is_approved = True
        
    # TODO: also automatically approve comment if it's considered as safe:
    # i.e. without hyperlinks, spam etc
    
    # check how much hyperlinks in the body string
    if len(re.findall('https?://', body, flags=re.IGNORECASE)) <= 1:
        comment.is_approved = True

    article.comments_total += 1
    if comment.is_approved:
        article.comments_approved += 1

    # record commenter ip address
    comment.ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
    comment.xff_ip_address = request.environ.get('X_FORWARDED_FOR', None)

    dbsession.add(comment)
    dbsession.flush()
    dbsession.expunge(comment) # remove object from the session, object state is preserved
    dbsession.expunge(article)
    transaction.commit()
    
    # comment added, now send notifications
    cylce_limit = 100
    comment = dbsession.query(Comment).get(comment.id)
    parent = comment.parent
    admin_email = get_config('admin_notifications_email')
    vf_q = dbsession.query(VerifiedEmail)
    notifications_emails = list()
    
    while parent is not None and cylce_limit > 0:
        cylce_limit -= 1
        c = parent
        parent = c.parent
        # walk up the tree
        if not c.is_subscribed:
            continue
        # find email
        email = None
        if c.user is None:
            email = c.email
        else:
            email = c.user.email
            
        if email is None or email == admin_email:
            continue
        
        email = normalize_email(email)
        
        if email in notifications_emails:
            continue
        
        vf = vf_q.get(email)
        if vf is not None and vf.is_verified:
            # send notification to "email"
            ns.append(notifications.gen_comment_response_notification(request, article, comment, c, email))
    
    admin_notifications_email = normalize_email(get_config('admin_notifications_email'))
    
    for nfn in ns:
        if nfn.to == admin_notifications_email:
            continue
        nfn.send()
        
    # create special notification for the administrator
    nfn = notifications.gen_new_comment_admin_notification(request, article, comment)
    if nfn is not None:
        nfn.send()
            
    # cosntruct comment_id
    # we're not using route_url() for the article because stupid Pyramid urlencodes fragments
    comment_url = h.article_url(request, article) + '?commentid=' + str(comment.id)
    
    # return rendered comment
    data = dict(body=comment.rendered_body, approved=comment.is_approved, id=comment.id, url=comment_url)

    return data


@view_config(route_name='blog_approve_comment_ajax', renderer='json', request_method='POST', permission='admin')
def approve_article_comment_ajax(request):
    comment_id = int(request.matchdict['comment_id'])
    dbsession = DBSession()
    comment = dbsession.query(Comment).get(comment_id)
    if comment is None:
        return HTTPNotFound()

    # also find corresponding article
    article = dbsession.query(Article).get(comment.article_id)

    if article is None:
        return HTTPNotFound()

    orig = comment.is_approved
    transaction.begin()
    comment.is_approved = True

    if not orig:
        article.comments_approved += 1

    transaction.commit()
    data = dict()
    return data
    
@view_config(route_name='blog_delete_comment_ajax', renderer='json', request_method='POST', permission='admin')
def delete_article_comment_ajax(request):
    comment_id = int(request.matchdict['comment_id'])
    dbsession = DBSession()
    comment = dbsession.query(Comment).get(comment_id)
    if comment is None:
        return HTTPNotFound()
    
    transaction.begin()
    dbsession.delete(comment)
    transaction.commit()
    
    data = dict()
    return data

@view_config(route_name='blog_edit_comment_fetch_ajax', renderer='json', request_method='POST', permission='admin')
def edit_fetch_comment_ajax(request):
    """
    Fetch comment details
    """
    comment_id = int(request.matchdict['comment_id'])
    dbsession = DBSession()
    
    comment = dbsession.query(Comment).get(comment_id)
    
    attrs = ('display_name', 'email', 'website', 'body', 'ip_address', 'xff_ip_address')
    data = dict()
    for a in attrs:
        data[a] = getattr(comment, a)

    data['date'] = h.timestamp_to_str(comment.published)

    return data
    

@view_config(route_name='blog_edit_comment_ajax', renderer='json', request_method='POST', permission='admin')
def edit_article_comment_ajax(request):
    """
    Update comment and return updated and rendered data
    """
    comment_id = int(request.matchdict['comment_id'])
    dbsession = DBSession()
    
    transaction.begin()
    comment = dbsession.query(Comment).options(eagerload('user')).options(eagerload('user.permissions')).get(comment_id)

    # passed POST parameters are: 'body', 'name', 'email', 'website', 'date', 'ip', 'xffip'
    params = dict(body='body', name='display_name', email='email', website='website',
                 ip='ip_address', xffip='xff_ip_address')

    for k,v in params.iteritems():
        value = request.POST[k]
        if value == '':
            value = None
        setattr(comment, v, value)

    comment.set_body(request.POST['body'])

    comment.published = h.str_to_timestamp(request.POST['date'])
    dbsession.flush()
    
    #comment_user = None
    #if comment.user is not None:
    #    comment_user = dbsession.query(User).options(eagerload('permissions')).get(comment.user)
    
    dbsession.expunge(comment)
    if comment.user is not None:
        dbsession.expunge(comment.user)
        for p in comment.user.permissions:
            dbsession.expunge(p)
    transaction.commit()

    data = dict()

    # without "unicode" or "str" it generates broken HTML
    # because render() returns webhelpers.html.builder.literal
    renderer_dict = dict(comment=comment)
    if comment.user is not None:
        comment._real_email = comment.user.email
    else:
        comment._real_email = comment.email
        
    if comment._real_email == '':
        comment._real_email = None
    data['rendered'] = render('/blog/single_comment.mako', renderer_dict, request)
    return data

@view_config(route_name='blog_download_file')
def download_file(request):
    filename = request.matchdict['filename']
    
    dbsession = DBSession()
    file = dbsession.query(File).filter(File.name==filename).first()
    
    if file is None:
        return HTTPNotFound()
    
    #headers = [('Content-Type', file.content_type), ('Content-Length', str(file.size))]
    headers = []
    dltype = file.dltype
    
    if 'dltype' in request.GET and request.GET['dltype'] in allowed_dltypes:
        dltype = request.GET['dltype']
        
    if dltype == 'download':
        headers.append( ('Content-Disposition', 'attachment; filename=%s' % file.name) )
    else: #if file.dltype == 'auto':
        pass
    
    storage_dirs = get_storage_dirs()
    full_path = os.path.join(storage_dirs['orig'], filename)
    try:
        content_length = os.path.getsize(full_path)
        headers += [('Content-Length', content_length)]
    except IOError:
        return HTTPNotFound()
    
    response = Response(content_type=file.content_type)
    try:
        response.app_iter = open(full_path, 'rb')
    except IOError:
        return HTTPNotFound()
    response.headerlist += headers
    
    return response

@view_config(route_name='blog_download_file_preview')
def download_file_preview(request):
    filename = request.matchdict['filename']
    
    dbsession = DBSession()
    file = dbsession.query(File).filter(File.name==filename).first()
    
    if file is None:
        return HTTPNotFound()

    if file.content_type not in ('image/jpeg', 'image/png', 'image/jpg'):
        return HTTPNotFound()

    headers = []
    dltype = file.dltype

    if 'dltype' in request.GET and request.GET['dltype'] in allowed_dltypes:
        dltype = request.GET['dltype']
        
    if dltype == 'download':
        headers.append( ('Content-Disposition', 'attachment; filename=preview_%s' % file.name) )

    storage_dirs = get_storage_dirs()
    full_path = os.path.join(storage_dirs['orig'], filename)
    preview_path = os.path.join(storage_dirs['img_preview_mid'], filename)
    preview_path += '.png' # always save preview in PNG format

    if os.path.exists(preview_path) and not os.path.isfile(preview_path):
        log.error('Path to preview image "%s" must be a regular file!' % preview_path)
        return HTTPServerError()
    
    # make preview image if required
    if not os.path.exists(preview_path):
        try:
            preview_max_width = int(get_config('image_preview_width', 300))
        except ValueError:
            preview_max_width = 300
        except TypeError:
            preview_max_width = 300
        im = Image.open(full_path)
        if im.size[0] <= preview_max_width:
            # don't need a resize
            preview_path = full_path
        else:
            h = (im.size[1] * preview_max_width) / im.size[0]
            resized = im.resize((preview_max_width, int(h)), Image.BILINEAR)
            resized.save(preview_path)
    
    try:
        content_length = os.path.getsize(preview_path)
        headers += [('Content-Length', content_length)]
    except IOError:
        return HTTPNotFound()
    
    response = Response(content_type=file.content_type)
    try:
        response.app_iter = open(preview_path, 'rb')
    except IOError:
        return HTTPNotFound()
    response.headerlist += headers
    
    return response
