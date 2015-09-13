import errno
import json
import os
import random
import sublime
import sublime_plugin
import sys
import urllib
from threading import Thread

global xkcd_open
xkcd_open = []

if sys.version_info < (3, 3):
    raise RuntimeError('Xkcd works with Sublime Text 3 only')


def plugin_loaded():
    """Called directly from sublime on plugin load."""
    try:
        os.makedirs(sublime.cache_path() + os.path.sep + 'Xkcd')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise IOError('Error encountered during file creation.')


def plugin_unloaded():
    """Called directly from sublime on plugin unload."""
    clean_cache()


def clean_cache():
    """Delete cache"""
    for fl in os.listdir(sublime.cache_path() + os.path.sep + 'Xkcd'):
        try:
            os.remove(sublime.cache_path() + os.path.sep + 'Xkcd' + os.path.sep + fl)
        except OSError as e:
            raise IOError('Could not remove previous files.')


def xJson(id=None):
    """Get JSON object from XKCD API."""
    if id is None:
        url = 'http://xkcd.com/info.0.json'
    else:
        url = 'http://xkcd.com/' + str(id) + '/info.0.json'

    try:
        request = urllib.request.Request(url, headers={"User-Agent":
                                                       "Sublime Xkcd"})
        opener = urllib.request.build_opener()
        f = opener.open(request)
        result = json.loads(f.read().decode("utf-8"))

        return result

    except urllib.error.HTTPError as e:
        sublime.error_message('Xkcd: %s: HTTP error %s contacting API' % (__name__, str(e.code)))
    except urllib.error.URLError as e:
        sublime.error_message('Xkcd: %s: URL error %s contacting API' % (__name__, str(e.reason)))


class EventDump(sublime_plugin.EventListener):

    """Event listener for automatic closing of meta-pane on image close."""

    global xkcd_open

    def on_activated(self, view):
        """View activated."""
        if xkcd_open:
            try:
                xkcd_open.pop()
            except Exception as e:
                print(str(e))
            if view.file_name() != None:
                view.window().run_command(
                    "hide_panel", {"panel": "output.xkcd_meta"})


    def on_close(self, view):
        """View closed."""
        clean_cache()


class XkcdGetComicCommand(sublime_plugin.WindowCommand):

    """Grab comic."""

    def run(self, kind):
        """Main function, runs on activation."""
        # Grab comic via async background process
        if kind == 'latest':
            thread = Thread(target=self.getComic)
        elif kind == 'random':
            thread = Thread(target=self.getRandomComic)
        elif kind == 'list':
            thread = Thread(target=self.getList)
        thread.start()

    def getComic(self, id=None):
        """Background loop."""
        result = xJson(id)

        if result is not None:
            self.title = result['title']
            self.img = result['img']
            self.alt = result['alt']
            self.num = result['num']

            try:
                local_img = sublime.cache_path() + os.path.sep + 'Xkcd' + \
                    os.path.sep + self.img.split('/')[-1]
                urllib.request.urlretrieve(self.img, local_img)

            except urllib.error.HTTPError as e:
                sublime.error_message('Xkcd: %s: HTTP error %s retrieving image' % (__name__, str(e.code)))
            except urllib.error.URLError as e:
                sublime.error_message('Xkcd: %s: URL error %s retrieving image' % (__name__, str(e.reason)))

            self.output = '[' + str(self.num) + '] ' + \
                self.title + '\n\n' + self.alt

            panel = self.window.create_output_panel('xkcd_meta')
            panel.run_command('erase_view')
            self.window.run_command(
                "show_panel", {"panel": "output.xkcd_meta"})
            self.window.get_output_panel('xkcd_meta').run_command(
                'append', {'characters': self.output})
            panel.settings().set("word_wrap", True)
            # print(int(self.window.active_view().viewport_extent()[0]-self.window.active_view().layout_extent()[0]))

            self.window.open_file(local_img, sublime.TRANSIENT)

            global xkcd_open
            xkcd_open.append(self.num)

            # HANDLE NAVIGATION (first/previous/next/last) HERE...
        else:
            sublime.error_message('Xkcd: Error reading API response')

    def getRandomComic(self):
        """Background loop."""
        latest = xJson()
        self.getComic(random.randrange(latest['num']))

    def getList(self):
        """Background loop."""
        url = 'http://xkcd.com/archive/'
        try:
            xml_str = str(urllib.request.urlopen(url).read()).split(
                '(Hover mouse over title to view publication date)<br /><br />',
                1)[-1].split(
                '</div>\\n<div id="bottom" class="box">', 1)[0].strip()
        except urllib.error.URLError as e:
            print ('Xkcd: %s: URL error %s reading list' % (__name__, str(e.reason)))
        clean_xml_str = xml_str.split('<br/>')

        self.menu_list = []
        for line in clean_xml_str:
            if line is not None:
                line_id = line.split('"/', 1)[-1].split('/"', 1)[0]
                line_date = line.split('="', 2)[-1].split('">', 1)[0]
                line_title = line.split('">', 1)[-1].split('</', 1)[0]
                self.menu_list.append([line_title, line_id, line_date])

        sublime.set_timeout_async(self.window.show_quick_panel(
            self.menu_list, self.on_chosen), 0)

    def on_chosen(self, index):
        """Comic chosen from quick panel."""
        if index is not -1:
            thread = Thread(
                target=self.getComic, args=(self.menu_list[index][1],))
            thread.start()


class XkcdLatestCommand(sublime_plugin.WindowCommand):

    """Latest Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        self.window.run_command(
            'xkcd_get_comic', {'kind': 'latest'}
        )


class XkcdRandomCommand(sublime_plugin.WindowCommand):

    """Random Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        self.window.run_command(
            'xkcd_get_comic', {'kind': 'random'}
        )


class XkcdListCommand(sublime_plugin.WindowCommand):

    """List Xkcd."""

    def run(self):
        """Main function, runs on activation."""
        self.window.run_command(
            'xkcd_get_comic', {'kind': 'list'}
        )
