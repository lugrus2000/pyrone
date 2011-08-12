<%
    authenticated = h.auth.get_user(request).kind != 'anonymous'
    
    writer_permission = user.has_permission('write_article')
    editor_permission = user.has_permission('edit_article')
    admin_permission = user.has_permission('admin')
%>
% if authenticated:

<div class="widget">
  <div class="section">${_('Actions')}</div>
% if writer_permission:
  <div><a href="${url('blog_write_article')}">${_('Write new article')}</a></div>
% endif
% if admin_permission:
  <div><a href="${url('admin_settings')}">${_('Settings')}</a></div>
  <div><a href="${url('admin_list_accounts')}">${_('Accounts')}</a></div>
  <div><a href="${url('admin_list_files')}">${_('Manage files')}</a></div>
  <div><a href="${url('admin_list_backups')}">${_('Backup/restore')}</a></div>
% endif
</div>
% endif