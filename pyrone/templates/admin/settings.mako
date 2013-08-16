<%inherit file="/admin/base.mako"/>

<%def name="title()">${_('Blog settings')}</%def>

<h2>${_('Blog settings')}</h2>

<script language="javascript">
$(window).scroll(function() {
    var top = $(this).scrollTop();
    var el = $('#settings-save-button-block');
    if (top <= 55) {
        el.css('position', 'absolute').css('top', '0px').css('border', '1px solid white');
    } else {
        el.css('position', 'fixed').css('top', '0').css('border', '1px solid gray');
    }
    //.css('top', $(this).scrollTop() + "px")
});
</script>

<form action="/" onsubmit="Pyrone_settings_saveSettings('${url('admin_settings_save_ajax')}'); return false;">
  <div id="settings-save-button-block"><div><input type="submit" value="${_('save')}"/></div> <div class="notify" style="display:none;" id="eid-notify"></div></div>
<dl class="form">
  <h3>${_('General')}</h3>
  ${h.form_input_text('site_title', _('Blog title'), settings['site_title'], errors)|n}
  ${h.form_input_text('site_base_url', _('Base blog address'), settings['site_base_url'], errors,\
    help=_('URL that will be used in all external communications (notification messages for example)'))|n}
  ${h.form_input_text('site_copyright', _('Copyright string'), settings['site_copyright'], errors,\
    help=_(u'A string displayed at the bottom of each blog page, just before “Powered by Pyrone”'))|n}
  ${h.form_input_text('elements_on_page', _('Number of elements on a page'), settings['elements_on_page'], errors,\
    help=_(u'How much elements (articles etc) display on single page'))|n}
  ${h.form_input_text('site_style', _('Blog style (skin)'), settings['site_style'], errors)|n}
  ${h.form_input_text('image_preview_width', _('Picture preview width'), settings['image_preview_width'], errors,\
    help=_(u'Width of automatically generated preview to be used as smaller copy of original picture.'))|n}
  ${h.form_input_text('google_analytics_id', _(u'Google Analytics™ ID'), settings['google_analytics_id'], errors,\
    help=_(u'Your google analytics ID, value like “UA-12345678-9”, to disable Google Analytics just clear the field'))|n}
  ${h.form_input_text('timezone', _(u'Blog timezone'), settings['timezone'], errors,\
    help=_(u'Timezone to be used for time and date values on the site, <strong>must</strong> be tzdb-compatible string value like “Asia/Novosibirsk” or “UTC”.'))|n}
  ${h.form_selector('ui_lang', _(u'Site language'), h.get_supported_langs_spec().items(),
    settings['ui_lang'], errors )|n}
  
  <h3>${_('Twitter Auth')}</h3>
  <dt><strong>${_('To use Twitter authentication you MUST <a href="https://dev.twitter.com/apps">register</a> a new twitter application and obtain consumer key and secret.')|n}</strong></dt>
  ${h.form_input_text('tw_consumer_key', _('Consumer key'), settings['tw_consumer_key'], errors)|n}
  ${h.form_input_text('tw_consumer_secret', _('Consumer secret'), settings['tw_consumer_secret'], errors)|n}
  
  <h3>${_(u'Twitter “share a link” button')}</h3>
  ${h.form_checkbox('social_twitter_share_link', None, settings['social_twitter_share_link'] == 'true', errors, 
    label=_('enable this social button'))|n}
  ${h.form_checkbox('social_twitter_share_link_show_count', None, settings['social_twitter_share_link_show_count'] == 'true', errors, 
    label=_('show total Twitter recommendations count'))|n}
  ${h.form_input_text('social_twitter_share_link_via', _('Use this Twitter username for sharing'), settings['social_twitter_share_link_via'], errors)|n}

  <h3>${_(u'Google “+1” button')}</h3>
  ${h.form_checkbox('social_gplusone', None, settings['social_gplusone'] == 'true', errors, 
    label=_('enable this social button'))|n}

  <h3>${_('Site search widget')}</h3>
  ${h.form_textarea('site_search_widget_code', _('HTML/JavaScript code for the site search widget'), settings['site_search_widget_code'], errors,\
    help=_('You should enter HTML code in this text box you received from the external search provider. To delete site search from the pages just clear the field.'),\
    height=150)|n}

  <h3>${_('Notifications')}</h3>
  ${h.form_input_text('admin_notifications_email', _('Email address for system notifications'), settings['admin_notifications_email'], errors,
    help=_('Email address for the system notification: user added, comment added for moderation etc'))|n}
  
  ${h.form_input_text('notifications_from_email', _('Email address to be used as sender address'), settings['notifications_from_email'], errors,
    help=_('This email will be used as FROM address for notification messages'))|n}
    
  <dt>${_('Select notifications you want to receive')}</dt>
  ${h.form_checkbox('admin_notify_new_comments', None, settings['admin_notify_new_comments'] == 'true', errors, 
  	label=_('new comment added (including comment moderation requests)'))|n}
  ${h.form_checkbox('admin_notify_new_user', None, settings['admin_notify_new_user'] == 'true', errors, 
  	label=_('new user registered'))|n}

  ${h.form_input_text('verification_msg_subject_tpl', _('Email address verification message subject template'), settings['verification_msg_subject_tpl'],
    errors, help=_('Plain text, no HTML, allowed substitution symbols:') + '{site_title}')|n}
  ${h.form_textarea('verification_msg_body_tpl', _('Email address verification message body template'), settings['verification_msg_body_tpl'],
    errors, help=_('Plain text, no HTML, allowed substitution symbols:') + '{site_title}, {email}, {verify_link}', height=150)|n}
    
  ${h.form_input_text('comment_answer_msg_subject_tpl', _('Answer to comment notification message subject template'),\
  	settings['comment_answer_msg_subject_tpl'],
    errors, help=_('Plain text, no HTML, allowed substitution symbols:') + '{article_title}, {comment_author_name}, {comment_author_email}, {site_title}')|n}
  ${h.form_textarea('comment_answer_msg_body_tpl', _('Answer to comment notification message body template'), 
  	settings['comment_answer_msg_body_tpl'], errors, \
  	help=_('Plain text, no HTML, allowed substitution symbols:') + '{comment_date}, {comment_author_name}, \
{comment_author_email}, {comment_text}, {comment_link}, {article_title}, {article_link}', height=150)|n}
    
  ${h.form_input_text('admin_notify_new_comment_subject_tpl', _('Admin notification subject template: new comment'),\
  	settings['admin_notify_new_comment_subject_tpl'],
    errors, help=_('Plain text, no HTML, allowed substitution symbols:') + '{article_title}, {comment_author_name}, \
{comment_author_email}, {site_title}')|n}
  ${h.form_textarea('admin_notify_new_comment_body_tpl', _('Admin notification body template: new comment'), 
  	settings['admin_notify_new_comment_body_tpl'], errors, \
  	help=_('Plain text, no HTML, allowed substitution symbols:') + '{comment_date}, {comment_author_name}, \
{comment_author_email}, {comment_text}, {comment_link}, {article_title}, {article_link}', height=150)|n}
    
  ${h.form_input_text('admin_notify_new_user_subject_tpl', _('Admin notification subject template: new user registered'),\
  	settings['admin_notify_new_user_subject_tpl'],
    errors, help=_('Plain text, no HTML, allowed substitution symbols:') + '{user}')|n}
  ${h.form_textarea('admin_notify_new_user_body_tpl', _('Admin notification body template: new user registered'), 
  	settings['admin_notify_new_user_body_tpl'], errors, \
  	help=_('Plain text, no HTML, allowed substitution symbols:') + '{user}, \
    {answer_title}, {answer_body}, {email}', height=150)|n}
    
</dl>
</form>
