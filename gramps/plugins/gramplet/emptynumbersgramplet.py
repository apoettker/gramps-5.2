# encoding:utf-8
#
# Gramps - a GTK+/GNOME based genealogy program - Records plugin
#
# Copyright (C) 2025 Alois Poettker
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------
from gi.repository import Gtk

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext

from gramps.gui import widgets
from gramps.gen.plug import Gramplet
from gramps.gui.filters.sidebar import SidebarFilter

def extract_text(entry_widget):
    """
    Extract the text from the entry widget, strips off any extra spaces,
    and converts the string to unicode. For some strange reason a gtk bug
    prevents the extracted string from being of type unicode.
    """
    return str(entry_widget.get_text().strip())

# -------------------------------------------------------------------------
#
# EmptyNumber
#
# -------------------------------------------------------------------------

class EmptyNumberList(object):
    """"""

    def __init__(self, dbstate, uistate):
        """"""
        self.dbstate = dbstate
        self.uistate = uistate

        self.obj_filter = 1
        self.obj_list = []
        self.obj_dict = {
            1: [], 2: [], 3: [], 10: [],
            'dummy': [], 'odd': [], 'even': [], 'oo': []
        }

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.output = self.add_text_view()

    def clicked(self, obj):
        self.get_filter()

        self.uistate.set_busy_cursor(True)
        self.get_gid_list()
        self.filter_gid_list()
        self.display_gid_list()
        self.uistate.set_busy_cursor(False)

    def clear(self, obj):
        """"""
        self.obj_filter = 1
        for obj in self.obj_dict:   # obj_dict clear!
            self.obj_dict[obj].clear()

        self.output.set_text('', -1)   # clear TextBuffer!

    def get_filter(self):
        pass

    def get_gid_list(self):
        pass

    def filter_gid_list(self):
        pass

    def display_gid_list(self):
        # Displaying data

        self.output.set_text('', -1)   # clear TextBuffer!
        output_list = []
        if self.obj_filter in [1, 'even', 'odd']:
            for val in self.obj_dict[self.obj_filter]:
                output_list.append('%s\n' % val)
        elif self.obj_filter in [2, 3, 5, 10, 50, 'oo']:
            for val in self.obj_dict[self.obj_filter]:
                output_list.append('%s -- %s\n' % (val[0], val[1]))
        elif self.obj_filter == 'dummy':
            for val in self.obj_dict[self.obj_filter]:
                output_list.append('%s\n' % val['gid'])
        output_list.append("\n")

        self.output.set_text(''.join(output_list))

    def cb_filter_type(self, widget):
        """"""
        self.get_filter()
        self.display_gid_list()

    def add_text_view(self):
        """
        Add a text view to the interface.
        """
        swin = Gtk.ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.IN)
        tview = Gtk.TextView()
        tview.set_left_margin(6)
        swin.add(tview)
        self.vbox.pack_start(swin, True, True, 6)

        return tview.get_buffer()

# ------------------------------------------------------------------------
#
# EmptyPersonNumbersFilter
#
# ------------------------------------------------------------------------
class PersonEmptyNumbersFilter(EmptyNumberList, SidebarFilter):
    def __init__(self, dbstate, uistate, clicked=None):
        """"""
        EmptyNumberList.__init__(self, dbstate, uistate)

        self.filter_type = Gtk.ComboBoxText()
        list(map(self.filter_type.append_text,
                [
                     _("1 Leerst."),
                     _("gerade Leerst."),
                     _("ungerade Leerst."),
                     _("2 Leerst."),
                     _("3 Leerst."),
                     _("> 10 Leerst."),
                     _("oo Leerst."),
                     _("Dummy"),
                ],
        ))
        self.filter_type.set_active(0)

        SidebarFilter.__init__(self, dbstate, uistate, "EmptyNumbers")

    def create_widget(self):
        """"""
        self.add_entry(None, self.filter_type)
        self.filter_type.connect('changed', self.cb_filter_type)

    def get_widget(self):
        """"""
        self.output = self.add_text_view()

        return self.vbox

    def get_filter(self):
        # check the type, and select the right rule based on type
        self.obj_filter = 1
        match self.filter_type.get_active():
            case 0: pass
            case 1: self.obj_filter = 'even'
            case 2: self.obj_filter = 'odd'
            case 3: self.obj_filter = 2
            case 4: self.obj_filter = 3
            case 5: self.obj_filter = 10
            case 7: self.obj_filter = 'dummy'
            case _: self.obj_filter = 'oo'

    def get_gid_list(self):
        # Collecting data
        cursor = self.dbstate.db.get_person_cursor()
        data = next(cursor)
        self.obj_dict['dummy'].clear()
        while data:
            last_name = ''
            (handle, val) = data
            if val[3] and val[3][5] and val[3][5][0]:
                last_name = val[3][5][0][0]
                if last_name == 'Dummy':
                    obj = {'gid': val[1], 'handle': handle}
                    self.obj_dict['dummy'].append(obj)
            self.obj_list.append(int(val[1][1:]))
            data = next(cursor)
        cursor.close()
        self.obj_list.sort()
        self.obj_dict['dummy'] = sorted(self.obj_dict['dummy'], key=lambda x: x['gid'])

    def filter_gid_list(self):
        # Filtering data
        format_obj = "person_prefix"
        prefix_obj = getattr(self.dbstate.db, format_obj)

        for obj in self.obj_dict:   # obj_dict clear!
            if obj == 'dummy': continue
            self.obj_dict[obj].clear()
        for no in range(1, len(self.obj_list)):
            seq_base = self.obj_list[no -1]
            seq_diff = self.obj_list[no] - seq_base
            if seq_diff == 1: continue
            sect_act = seq_base +1

            if seq_diff == 2:
                self.obj_dict[1].append(prefix_obj % sect_act)
                if sect_act % 2 == 0:
                    self.obj_dict['even'].append(prefix_obj % sect_act)
                else:
                    self.obj_dict['odd'].append(prefix_obj % sect_act)
            elif seq_diff == 3:
                self.obj_dict[2].append([prefix_obj % (sect_act), prefix_obj % (seq_base +2)])
            elif seq_diff == 4:
                self.obj_dict[3].append([prefix_obj % (sect_act), prefix_obj % (seq_base +3)])
            elif seq_diff > 100:
                self.obj_dict['oo'].append([prefix_obj % (sect_act), prefix_obj % (self.obj_list[no] -1)])
            elif seq_diff > 10:
                self.obj_dict[10].append([prefix_obj % (sect_act), prefix_obj % (self.obj_list[no] -1)])


# ------------------------------------------------------------------------
#
# EmptyFamilyNumbersFilter
#
# ------------------------------------------------------------------------
class FamilyEmptyNumbersFilter(EmptyNumberList, SidebarFilter):
    def __init__(self, dbstate, uistate, clicked=None):
        """"""
        EmptyNumberList.__init__(self, dbstate, uistate)

        self.filter_type = Gtk.ComboBoxText()
        list(map(self.filter_type.append_text,
                [
                     _("1 Leerst."),
                     _("2 Leerst."),
                     _("3 Leerst."),
                     _("> Leerst."),
                ],
        ))
        self.filter_type.set_active(0)

        SidebarFilter.__init__(self, dbstate, uistate, "EmptyNumbers")

    def create_widget(self):
        """"""
        self.add_entry(None, self.filter_type)
        self.filter_type.connect('changed', self.cb_filter_type)

    def get_widget(self):
        """"""
        self.output = self.add_text_view()

        return self.vbox

    def get_filter(self):
        # check the type, and select the right rule based on type
        self.obj_filter = 1
        match self.filter_type.get_active():
            case 0: pass
            case 1: self.obj_filter = 2
            case 2: self.obj_filter = 3
            case _: self.obj_filter = 'oo'

    def get_gid_list(self):
        # Collecting data
        cursor = self.dbstate.db.get_family_cursor()
        data = next(cursor)
        while data:
            (handle, val) = data
            self.obj_list.append(int(val[1][1:]))
            data = next(cursor)
        cursor.close()
        self.obj_list.sort()

    def filter_gid_list(self):
        # Filtering data
        format_obj = "family_prefix"
        prefix_obj = getattr(self.dbstate.db, format_obj)

        for obj in self.obj_dict:   # obj_dict clear!
            self.obj_dict[obj].clear()
        for no in range(1, len(self.obj_list)):
            seq_base = self.obj_list[no -1]
            seq_diff = self.obj_list[no] - seq_base
            if seq_diff == 1: continue
            sect_act = seq_base +1

            if seq_diff == 2:
                self.obj_dict[1].append(prefix_obj % sect_act)
            elif seq_diff == 3:
                self.obj_dict[2].append([prefix_obj % (sect_act), prefix_obj % (seq_base +2)])
            elif seq_diff == 4:
                self.obj_dict[3].append([prefix_obj % (sect_act), prefix_obj % (seq_base +3)])
            else:
                self.obj_dict['oo'].append([prefix_obj % (sect_act), prefix_obj % (self.obj_list[no] -1)])


# ------------------------------------------------------------------------
#
# EmptyNumbersGramplet
#
# ------------------------------------------------------------------------

class EmptyNumbers(Gramplet):
    FILTER_CLASS = None

    def init(self):
        self.filter = self.FILTER_CLASS(
            self.dbstate, self.uistate, None # self.__filter_clicked
        )
        self.widget = self.filter.get_widget()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.widget)
        self.widget.show_all()

# -------------------------------------------------------------------------
#
# PersonFilter class
#
# -------------------------------------------------------------------------
class PersonEmptyNumbers(EmptyNumbers):
    """
    A gramplet providing a Person Filter.
    """
    FILTER_CLASS = PersonEmptyNumbersFilter

# -------------------------------------------------------------------------
#
# FamilyFilter class
#
# -------------------------------------------------------------------------
class FamilyEmptyNumbers(EmptyNumbers):
    """
    A gramplet providing a Family Filter.
    """
    FILTER_CLASS = FamilyEmptyNumbersFilter
