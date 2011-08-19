from pyramid.config import Configurator
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_beaker import session_factory_from_settings
from sqlalchemy import engine_from_config

from pyrone.models import initialize_sql
from pyrone.lib.auth import PyroneSessionAuthenticationPolicy
from pyrone.models.file import init_storage_from_settings
#from pyrone.resources import RootFactory

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    initialize_sql(engine)
    session_factory = session_factory_from_settings(settings)
    init_storage_from_settings(settings)
    authentication_policy = PyroneSessionAuthenticationPolicy()
    authorization_policy = ACLAuthorizationPolicy()
    config = Configurator(settings=settings, session_factory=session_factory,
        root_factory='pyrone.resources.RootFactory',
        authentication_policy=authentication_policy,
        authorization_policy=authorization_policy)
    config.scan()
    config.add_static_view('static', 'pyrone:static')
    routes = [('blog_latest', '/'), 
              ('blog_tag_articles', '/tag/{tag}'),
              ('blog_write_article', '/write'), 
              ('blog_go_article', '/article/{article_id:\d+}'),
              ('blog_view_article', '/{shortcut_date:\d\d\d\d/\d\d/\d\d}/{shortcut}'),
              ('blog_edit_article', '/article/{article_id:\d+}/edit'),
              ('blog_preview_article', '/preview/article'),
              ('blog_article_delete_ajax', '/article/{article_id:\d+}/delete/ajax'),
              ('blog_edit_comment_ajax', '/comment/{comment_id:\d+}/edit/ajax'),
              ('blog_approve_comment_ajax', '/comment/{comment_id:\d+}/approve/ajax'),
              ('blog_delete_comment_ajax', '/comment/{comment_id:\d+}/delete/ajax'),
              ('blog_edit_comment_fetch_ajax', '/comment/{comment_id:\d+}/fetch/ajax'),
              ('blog_add_article_comment', '/article/{article_id:\d+}/comment'),
              ('blog_add_article_comment_ajax', '/article/{article_id:\d+}/comment/ajax'),
              
              ('account_my_profile', '/me'),
              ('account_save_my_profile_ajax', '/me/save/ajax'),
              ('account_login_form', '/login'),
              ('account_login', '/login'),
              ('account_logout', '/logout'),
              ('account_twitter_init', '/login/twitter/init'),
              
              ('blog_download_file', '/files/f/{filename}'),
              ('blog_download_file_preview', '/files/p/{filename}'),
              
              ('admin_settings', '/admin/settings'),
              ('admin_settings_save_ajax', '/admin/settings/save/ajax'),
              ('admin_list_files', '/admin/files'),
              ('admin_upload_file', '/admin/file/upload'),
              ('admin_upload_file_check_ajax', '/admin/file/upload/check'),
              ('admin_edit_file_props', '/admin/file/{file_id:\d+}/edit'),
              ('admin_edit_file_props_check_ajax', '/admin/file/{file_id:\d+}/edit/check'),
              ('admin_delete_files_ajax', '/admin/files/delete/ajax'),
              ('admin_list_accounts', '/admin/accounts'),
              ('admin_delete_accounts_ajax', '/admin/accounts/delete/ajax'),
              ('admin_list_backups', '/admin/backups'),
              ('admin_upload_backup', '/admin/backups/upload'),
              ('admin_delete_backups_ajax', '/admin/backups/delete/ajax'),
              ('admin_restore_backup', '/admin/backup/{backup_id}/restore'),
              ('admin_download_backup', '/admin/backup/{backup_id}/download'),
              ('admin_backup_now', '/admin/backup/now')
              ]
    for r in routes:
        config.add_route(*r)
        
    config.add_subscriber('pyrone.subscribers.add_renderer_globals', 'pyramid.events.BeforeRender')
    #config.add_subscriber('pyrone.subscribers.add_localizer', 'pyramid.events.NewRequest')
    
    #config.add_view('pyrone.views.latest',
    #                route_name='latest',
    #                renderer='templates/mytemplate.pt')
    return config.make_wsgi_app()