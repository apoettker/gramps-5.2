"""
Family Lines, a Graphviz-based plugin for Gramps.
"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import collections, collections.abc, copy, datetime, math, json, sys
import itertools
from functools import partial

# Graph-Tool ------------------------------------------------------------
from graph_tool import Graph
from graph_tool.topology import *
from graph_tool.util import *
gtG = Graph()

# IGraph ----------------------------------------------------------------
# import igraph as ig
# igG = ig.Graph()   # 2022:10:20: no simple cycle available

#  NetworkX -------------------------------------------------------------
import networkx as nx
nxG = nx.Graph()

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
LOG = logging.getLogger(".FamilyLines")

#------------------------------------------------------------------------
#
# Gramps module
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

from gramps.gen.db import DbTxn
from gramps.gen.lib import EventRoleType, EventType, Person, Date
from gramps.gen.utils.file import media_path_full
from gramps.gen.utils.thumbnails import (get_thumbnail_path, SIZE_NORMAL, SIZE_LARGE)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import utils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.plug.menu import (NumberOption, ColorOption, BooleanOption, StringOption,
                                  EnumeratedListOption, PersonListOption,
                                  SurnameColorOption)
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback
from gramps.gen.utils.location import get_location_list
from gramps.gen.proxy import CacheProxyDb
from gramps.gen.errors import ReportError
from gramps.gen.display.place import displayer as _pd

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libcolor import Color
from gramps.plugins.libAP.libnameobject import ordName
from gramps.plugins.libAP.libnetwork import *

#------------------------------------------------------------------------
#
# Constant options items
#
#------------------------------------------------------------------------
_CHARTS = ["Board", "Implex", "Lineage"]
_HENRY = "123456789XABCDEFGHIJKLMNOPQRSTUVW"
_MALEXY = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]
_FEMALEXX = [1, 3, 7, 15, 31, 63, 127, 255, 511, 1023, 2047]
_XDNAOPTX1 = [1, 2, 5, 10, 21, 42, 85, 170, 341, 682, 1365]
_XDNAOPTX2 = [1, 6, 13, 26, 53, 106, 213, 426, 853, 1706]   # 3,
_LABELDIST = {1: 0.6, 2: 0.8, 3: 1.2, 4: 1.4, 5: 1.6, 6: 1.8, 7: 2.0, 8: 2.3, 9: 2.7, 10: 3.0, 11: 3.4, 12: 3.8, 13: 4.0}
_GENERATIONNAME_ = {'G00': 'Proband', 'G01': 'Kinder', 'G02': 'Enkel', 'G03': 'Urenkel', 'G04': 'Ur(x2)enkel', \
                    'G05': 'Ur(x3)enkel', 'G06': 'Ur(x4)enkel', 'G07': 'Ur(x5)enkel', 'G08': 'Ur(x6)enkel', \
                    'G09': 'Ur(x7)enkel', 'G10': 'Ur(x8)enkel', 'G11': 'Ur(x9)enkel', 'G12': 'Ur(x10)enkel', \
                    'G13': 'Ur(x11)enkel', 'G14': 'Ur(x12)enkel', 'G15': 'Ur(x13)enkel', 'G16': 'Ur(x14)enkel'
                    }

_COLORS = [{'name' : _("B&W outline"), 'value' : "outline"},
           {'name' : _("Colored outline"), 'value' : "colored"},
           {'name' : _("Color fill"), 'value' : "filled"}]

_ARROWS = [ { 'name' : _("descendants <- Ancestors"),  'value' : 'd' },
            { 'name' : _("descendants -> Ancestors"),  'value' : 'a' },
            { 'name' : _("descendants <-> Ancestors"), 'value' : 'da' },
            { 'name' : _("descendants - Ancestors"),   'value' : '' }]

_CORNERS = [ { 'name' : _("None"),  'value' : '' },
             { 'name' : _('female'), 'value' : 'f' },
             { 'name' : _('male'),   'value' : 'm' },
             { 'name' : _("Both"),  'value' : 'fm' }]
_INVIS_NODE = 'Invis [ height=0, width=0, margin=0, color="red" ]' # style=invis,

#------------------------------------------------------------------------
#
# A quick overview of the classes we'll be using:
#
#   class FamilyLinesOptions(MenuReportOptions)
#       - this class is created when the report dialog comes up
#       - all configuration controls for the report are created here
#
#   class FamilyLinesReport(Report)
#       - this class is created only after the user clicks on "OK"
#       - the actual report generation is done by this class
#
#------------------------------------------------------------------------

class FamilyLinesOptions(MenuReportOptions):
    """
    Defines all of the controls necessary
    to configure the FamilyLines report.
    """
    def __init__(self, name, dbase):
        self.limit_parents = None
        # self.max_parents_number = None
        # self.max_parents_generation = None
        self.limit_children = None
        # self.max_children_number = None
        # self.max_children_generation = None
        self.diagram_images = None
        self.image_location = None
        self.justyears = None
        self.diagram_dates = None
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):

        # ---------------------
        category_name = _('Report Options')
        add_option = partial(menu.add_option, category_name)
        # ---------------------

        followpar = BooleanOption(_('Follow parents to determine '
                                    '"family lines"'), True)
        followpar.set_help(_('Parents and their ancestors will be '
                             'considered when determining "family lines".'))
        add_option('followpar', followpar)

        followchild = BooleanOption(_('Follow children to determine '
                                      '"family lines"'), True)
        followchild.set_help(_('Children will be considered when '
                               'determining "family lines".'))
        add_option('followchild', followchild)

        remove_extra_people = BooleanOption(_('Try to remove extra '
                                              'people and families'), True)
        remove_extra_people.set_help(_('People and families not directly '
                                       'related to people of interest will '
                                       'be removed when determining '
                                       '"family lines".'))
        add_option('removeextra', remove_extra_people)

        arrow = EnumeratedListOption(_("Arrowhead direction"), 'd')
        for i in range( 0, len(_ARROWS) ):
            arrow.add_item(_ARROWS[i]["value"], _ARROWS[i]["name"])
        arrow.set_help(_("Choose the direction that the arrows point."))
        add_option("arrow", arrow)

        color = EnumeratedListOption(_("Graph coloring"), "filled")
        for i in range(len(_COLORS)):
            color.add_item(_COLORS[i]["value"], _COLORS[i]["name"])
        color.set_help(_("Males will be shown with blue, females "
                         "with red, unless otherwise set above for filled. "
                         "If the sex of an individual "
                         "is unknown it will be shown with gray."))
        add_option("color", color)

        roundedcorners = EnumeratedListOption(_("Rounded corners"), '')
        for i in range( 0, len(_CORNERS) ):
            roundedcorners.add_item(_CORNERS[i]["value"], _CORNERS[i]["name"])
        roundedcorners.set_help(_("Use rounded corners e.g. to differentiate "
                         "between women and men."))
        add_option("useroundedcorners", roundedcorners)

        stdoptions.add_gramps_id_option(menu, category_name, ownline=True)

        # ---------------------
        category_name = _('Report Options (2)')
        add_option = partial(menu.add_option, category_name)
        # ---------------------

        stdoptions.add_name_format_option(menu, category_name)

        stdoptions.add_private_data_option(menu, category_name, default=False)

        stdoptions.add_living_people_option(menu, category_name)

        locale_opt = stdoptions.add_localization_option(menu, category_name)

        stdoptions.add_date_format_option(menu, category_name, locale_opt)

        # --------------------------------
        add_option = partial(menu.add_option, _('People of Interest'))
        # --------------------------------

        person_list = PersonListOption(_('People of interest'))
        person_list.set_help(_('People of interest are used as a starting '
                               'point when determining "family lines".'))
        add_option('gidlist', person_list)

        self.limit_parents = BooleanOption(_('Limit the number of ancestors'), False)
        self.limit_parents.set_help(_('Whether to '
                                      'limit the number of ancestors.'))
        add_option('limitparents', self.limit_parents)
        self.limit_parents.connect('value-changed', self.limit_changed)

        self.max_parents = NumberOption('', 50, 10, 9999)
        self.max_parents.set_help(_('The maximum number '
                                    'of ancestors to include.'))
        add_option('maxparents', self.max_parents)

        self.limit_children = BooleanOption(_('Limit the number of descendants'), False)
        self.limit_children.set_help(_('Whether to '
                                       'limit the number of descendants.'))
        add_option('limitchildren', self.limit_children)
        self.limit_children.connect('value-changed', self.limit_changed)

        self.max_children = NumberOption('', 50, 10, 9999)
        self.max_children.set_help(_('The maximum number '
                                     'of descendants to include.'))
        add_option('maxchildren', self.max_children)

        # --------------------
        category_name = _('Include')
        add_option = partial(menu.add_option, category_name)
        # --------------------

        self.diagram_id = EnumeratedListOption(_('Include Gramps ID'), False)
        self.diagram_id.add_item(0, _('Do not include'))
        self.diagram_id.add_item(1, _('Share an existing line'))
        self.diagram_id.add_item(2, _('On a line of its own'))
        self.diagram_id.set_help(_("Whether (and where) to include Gramps IDs"))
        add_option('incid', self.diagram_id)

        self.diagram_dates = BooleanOption(_('Include dates'), True)
        self.diagram_dates.set_help(_('Whether to include dates for people '
                                      'and families.'))
        add_option('incdates', self.diagram_dates)
        self.diagram_dates.connect('value-changed', self.include_dates_changed)

        self.justyears = BooleanOption(_("Limit dates to years only"), False)
        self.justyears.set_help(_("Prints just dates' year, neither "
                                  "month or day nor date approximation "
                                  "or interval are shown."))
        add_option("justyears", self.justyears)

        include_places = BooleanOption(_('Include places'), True)
        include_places.set_help(_('Whether to include placenames for people '
                                  'and families.'))
        add_option('incplaces', include_places)

        include_num_children = BooleanOption(_('Include the number of '
                                               'children'), True)
        include_num_children.set_help(_('Whether to include the number of '
                                        'children for families with more '
                                        'than 1 child.'))
        add_option('incchildcnt', include_num_children)

        self.diagram_images = BooleanOption(_('Include '
                                              'thumbnail images of people'),
                                            True)
        self.diagram_images.set_help(_('Whether to '
                                       'include thumbnail images of people.'))
        add_option('incimages', self.diagram_images)
        self.diagram_images.connect('value-changed', self.images_changed)

        self.image_location = EnumeratedListOption(_('Thumbnail location'), 0)
        self.image_location.add_item(0, _('Above the name'))
        self.image_location.add_item(1, _('Beside the name'))
        self.image_location.set_help(_('Where the thumbnail image '
                                       'should appear relative to the name'))
        add_option('imageonside', self.image_location)

        self.image_size = EnumeratedListOption(_('Thumbnail size'), SIZE_NORMAL)
        self.image_size.add_item(SIZE_NORMAL, _('Normal'))
        self.image_size.add_item(SIZE_LARGE, _('Large'))
        self.image_size.set_help(_('Size of the thumbnail image'))
        add_option('imagesize', self.image_size)

        # ----------------------------
        add_option = partial(menu.add_option, _('Family Colors'))
        # ----------------------------

        surname_color = SurnameColorOption(_('Family colors'))
        surname_color.set_help(_('Colors to use for various family lines.'))
        add_option('surnamecolors', surname_color)

        # -------------------------
        add_option = partial(menu.add_option, _('Individuals'))
        # -------------------------

        color_males = ColorOption(_('Males'), '#e0e0ff')
        color_males.set_help(_('The color to use to display men.'))
        add_option('colormales', color_males)

        color_females = ColorOption(_('Females'), '#ffe0e0')
        color_females.set_help(_('The color to use to display women.'))
        add_option('colorfemales', color_females)

        color_unknown = ColorOption(_('Unknown'), '#e0e0e0')
        color_unknown.set_help(_('The color to use '
                                 'when the gender is unknown.'))
        add_option('colorunknown', color_unknown)

        color_family = ColorOption(_('Families'), '#ffffe0')
        color_family.set_help(_('The color to use to display families.'))
        add_option('colorfamilies', color_family)

        data_set = StringOption('', '')
        add_option('data_set', data_set)

        self.limit_changed()
        self.images_changed()

    def limit_changed(self):
        """
        Handle the change of limiting parents and children.
        """
        self.max_parents.set_available(self.limit_parents.get_value())
        self.max_children.set_available(self.limit_children.get_value())

    def images_changed(self):
        """
        Handle the change of including images.
        """
        self.image_location.set_available(self.diagram_images.get_value())
        self.image_size.set_available(self.diagram_images.get_value())

    def include_dates_changed(self):
        """
        Enable/disable menu items if dates are required
        """
        if self.diagram_dates.get_value():
            self.justyears.set_available(True)
        else:
            self.justyears.set_available(False)


#------------------------------------------------------------------------
#
# FamilyLinesReport
#
#------------------------------------------------------------------------
class Node(dict):
    def __init__(self, art, pid, gender=2, fontsize=10, fixedsize=False):
        self.clear()
        self['art'] = art
        self['pid'] = pid
        self['gender'] = gender
        self['fontsize'] = fontsize
        self['fixedsize'] = fixedsize

        if art == 'I':   #  Individual
            if gender == 0: self['fillcolor'], self['bordercolor'] = '#FFE0E0', '#660000'   # Female: light / dark red
            elif gender == 1: self['fillcolor'], self['bordercolor'] = '#E0E0FF', '#000A66'   # Male: light / dark blue
            elif gender == 2: self['fillcolor'] = '#FFFFCC'   # Unknown: light yellow
        if art == 'F':   #  Family
            self['fillcolor'] = '#FFFFCC'   # light yellow

    def clear(self):
        self['art'], self['pid'], self['gender'] = '', '', ''
        self['type'] = '' # 'A'ncestor, 'P'roband, 'D'escendant
        self['base'] = False # base PID for XDNA
        self['label'] = ''
        self['shape'], self['style'] = '', ''
        self['bordercolor'], self['fillcolor'] = '#000000', '#FFFFFF'
        self['fontcolor'] = '#000000'
        self['extension'] = ''
        self['htmloutput'] = False

    def update(self, u):
        for k, v in u.items():
            if k not in ['fontcolor', 'fontsize', 'height', 'width', 'margin', 'penwidth', 'fontsize']:
                if isinstance(v, collections.abc.Mapping):
                    self[k] = self.update(self.get(k, {}), v)
                else:
                    self[k] = v

        self['extension'] = ''
        if keys_exists(u, 'fontcolor'): self['extension'] += 'fontcolor=%s ' % u['fontcolor']
        if keys_exists(u, 'fontsize'): self['extension'] += 'fontsize=%s ' % u['fontsize']

        if keys_exists(u, 'height'): self['extension'] += 'height=%s ' % u['height']
        if keys_exists(u, 'width'): self['extension'] += 'width=%s ' % u['width']
        if keys_exists(u, 'margin'): self['extension'] += 'margin=%s ' % u['margin']

        if keys_exists(u, 'penwidth'): self['extension'] += 'penwidth=%s ' % u['penwidth']
        if keys_exists(u, 'fontsize'): self['extension'] += 'fontsize=%s ' % u['fontsize']
        if keys_exists(u, 'fixedsize'): self['extension'] += 'fixedsize=%s ' % u['fixedsize']

        return True


class FamilyLinesReport(Report):
    """ FamilyLines report """

    def __init__(self, database, options, user):
        """
        Create FamilyLinesReport object that eventually produces the report.

        The arguments are:

        database     - the Gramps database instance
        options      - instance of the FamilyLinesOptions class for this report
        user         - a gen.user.User() instancesetup_style_frame
        name_format  - Preferred format to display names
        incl_private - Whether to include private data
        inc_id       - Whether to include IDs.
        living_people - How to handle living people
        years_past_death - Consider as living this many years after death
        """
        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.default_dataset()
        self.read_dataset(options)

        Report.__init__(self, database, options, user)

        self.set_locale(menu.get_option_by_name('trans').get_value())
        stdoptions.run_name_format_option(self, menu)
        stdoptions.run_date_format_option(self, menu)
        stdoptions.run_private_data_option(self, menu)
        stdoptions.run_living_people_option(self, menu, self._locale)
        self.database = CacheProxyDb(database)
        self.user = user

        # self.followparents = get_value('followpar')
        # self.followchildren = get_value('followchild')
        self.removeextra = False # get_value('removeextra')
        # self.include["pidlist"] = get_value('gidlist')
        # self.incimages = False # get_value('incimages')
        # self.imageonside = 0 # get_value('imageonside')
        # self.imagesize = get_value('imagesize')
        self.colorize = 'filled' # get_value('color')
        self.colormales = get_value('colormales')
        self.colorfemales = get_value('colorfemales')
        self.colorunknown = get_value('colorunknown')
        self.colorfamilies = get_value('colorfamilies')
        self.usesubgraphs = True # get_value('usesubgraphs')
        # self.diagramdates = get_value('incdates')
        self.diagram['dates']['onlyyears'] = True # get_value('justyears')
        # self.diagramplaces = get_value('incplaces')
        # self.diagramchildscount = get_value('incchildcnt')
        # self.diagramids = get_value('inc_id')
        # arrow_str = get_value('arrow')
        # self.arrowtailstyle = 'normal' if 'a' in arrow_str else 'none'
        # self.arrowheadstyle = 'normal' if 'd' in arrow_str else 'none'

        # the pidlist is annoying for us to use since we always have to convert
        # the PIDs to either Person or to handles, so we may as well convert the
        # entire list right now and not have to deal with it ever again
        if self.base["chart"].capitalize() in 'Board, Implex, Lineage' and \
           not self.include["pidlist"]:
            raise ReportError(_('Empty report'),
                              _('You did not specify anybody'))

        for key in self.dot:
            if hasattr(self.doc, key):
                if key == 'dpi': self.doc.dpi = self.dot[key]
                if key == 'bgcolor': self.doc.bgcolor = self.dot[key]
                if key == 'rankdir': self.doc.rankdir = self.dot[key]
                if key == 'concentrate': self.doc.concentrate = self.dot[key]
                if key == 'note': self.doc.note = self.dot[key]
                if key == 'fontfamily': self.doc.fontfamily = self.dot[key]
                if key == 'fontsize': self.doc.fontsize = self.dot[key]
                if key == 'fontextra': self.doc.fontextra = self.dot[key]
                if key == 'nodesep': self.doc.nodesep = self.dot[key]
                if key == 'ranksep': self.doc.ranksep = self.dot[key]
                if key == 'ratio': self.doc.ratio = self.dot[key]
                if key == 'sizew': self.doc.sizew = float(self.dot[key])
                if key == 'sizeh': self.doc.sizeh = float(self.dot[key])
                if key == 'spline': self.doc.spline = self.dot[key]
        # ource file will be copied to target directory as backup (graphdoc.py)
        self.doc.sourcefile = self.base['sourcefile']

    def _local_init(self):
        """"""
        # initialize several convenient variables
        self.people = {} # id of people we need in the report
        self.families = {} # id of families we need in the report
        self.parents = {} # id of parents we need in the report
        self.children = {} # id of children we need in the report
        self.generation = {} # id and generation of people we need in the report
        self.lineages = {} # pathes from people of source to people of target
        self.deleted_people = 0
        self.deleted_families = 0

        self.maxgeneration = max(self.maxparents_generation, self.maxchildren_generation)
        self.cutoffpath = 2 * (self.maxparents_generation + self.maxchildren_generation) +1 \
            if self.base["chart"].capitalize() == 'Implex' else 2 * self.maxgeneration +1

        self.interest_list, self.uninterest_list = [], []
        for pid in self.include["pidlist"]:
            person = self.database.get_person_from_gramps_id(pid)
            if person: # option can be from another family tree, so person can be None
                self.interest_list.append(pid)

        for ungid in self.include["unpidlist"]:
            person = self.database.get_person_from_gramps_id(ungid)
            if person: # option can be from another family tree, so person can be None
                self.uninterest_list.append(ungid)

        for key, value in self.include["fiddict"].items():
            family = self.database.get_family_from_gramps_id(key)
            if family:
                self.generation[key] = -value['generation'] -0.5
                self.families[key] = {
                    'type': value["type"],
                    'gen': value["generation"],
                    'handle': family.handle
                }
                father_handle = family.get_father_handle()
                # see if we have a father to link to this family
                if father_handle:
                    father = self.database.get_person_from_handle(father_handle)
                if father and father.gramps_id not in self.people:
                    self.generation[father.gramps_id] = value['generation'] +1
                    self.people[father.gramps_id] = {
                        'type': value["type"], 'PID': father.gramps_id ,
                        'handle': father_handle, 'spouse': False,
                        'EoL': False, 'XDNA': {}
                    }
                mother_handle = family.get_mother_handle()
                if mother_handle:
                    mother = self.database.get_person_from_handle(mother_handle)
                if mother and mother.gramps_id not in self.people:
                    self.generation[mother.gramps_id] = value['generation'] +1
                    self.people[mother.gramps_id] = {
                        'type': value['type'], 'PID': mother.gramps_id ,
                        'handle': mother_handle, 'spouse': True,
                        'EoL': False, 'XDNA': {}
                    }

        self.include['relativfamily'] = self.include['ancestorfamily']['enable'] or \
                                        self.include['descendantfamily']['enable']
        self.include['relativspouse'] = self.include['ancestorspouse']['enable'] or \
                                        self.include['descendantspouse']['enable']

        self.no_descendant_list = {}
        for nid in self.include["undescendantlist"]:
            if 'F' in nid:
                family = self.database.get_family_from_gramps_id(nid)
                if family:
                    for childRef in family.get_child_ref_list():
                        if not childRef.ref: continue

                        child = self.database.get_person_from_handle(childRef.ref)
                        if child and child.gramps_id not in self.no_descendant_list:
                            self.no_descendant_list[child.gramps_id] = childRef.ref
            if 'I' in nid:
                person = self.database.get_person_from_gramps_id(nid)
                # option can be from another family tree, so person can be None
                if person and person.gramps_id not in self.no_descendant_list:
                    self.no_descendant_list[person.gramps_id] = person.handle

        # Convert minLength string into list
        # self.minlengthlist = re.findall(r'\[([^]]*)\]', self.minlengthlist)
        # self.minlengthlist = list(filter(None, self.minlengthlist))

        # colorproband = self.color['proband'] if self.color['proband'] else get_value('surnamecolors')
        # self.color["ancestor"] = self.color['base'].string2name(self.color["ancestor"], self.color["threshold"])
        # self.color['proband'] = self.color['base'].string2name(self.color['proband'], self.color["threshold"])
        # self.color['descendant'] = self.color['base'].string2name(self.color['descendant'], self.color["threshold"])
        # self.color['additional'] = self.color['base'].string2name(self.color['additional'], self.color["threshold"])

        # Locale
        if keys_exists(self.base, 'locale'):
            self.set_locale(self.base['locale'])

        # Read!
        self.translate_dict = {}
        if keys_exists(self.base, 'translatefile'):
            with open(self.base['translatefile'], 'r') as file_handle:
                self.translate_dict = json.load(file_handle)

        return True

    def default_dataset(self):
        """"""
        self.base = {}
        self._base = {
            "chart": "Board",   # Board, Implex, Lineage
            "chart": "",   # "", Gradient, Level
            "locale": "default",

            "path": "",
            "databasefile": "",
            "sourcefile": "",
            "targetfile": "",
            "analyzefile": "",
            "addendumfile": "",
            "note": ""
        }

        self.maxparents_generation, self.maxchildren_generation, self.maxgeneration = 1, 1, 1
        self.maxspouse_generation = 0
        self.shift_generation = 0
        self.cutoffpath = 5   # 2* (self.maxparents_generation + self.maxchildren_generation) +1

        self.noderank, self.nodegroup, self.nodecluster = {}, {}, {}   #  Range: IND: horizontal, vertical, FAM: cluster
        self.noderotate, self.noteshift = [],{}   # Direction: horizontal, vertical

        self.include = {}
        self._include = {
            "pidlist": [],
            "unpidlist": [],
            "fiddict": {   # extra Families in Graph!
                "type": "", "generation": 0
            },
            "unfidlist": [],
            "undescendantlist": [],

            "ancestor": {"enable": False,
                         "color": False,
                         "images": {"enable": False, "exist": False, "onside": True},
                        },
            "ancestorspouse": {"enable": False,
                               "color": False,
                               "images": {"enable": False, "exist": False, "onside": True}
                              },
            "ancestorspouseparents": {"enable": False,
                               "color": False,
                               "images": {"enable": False, "exist": False, "onside": True}
                              },
            "ancestorfamily": {"enable": False,
                               "color": False,
                               "civil": False, "church": False, "line": False,
                               "childscount": False
                               },
            "ancestorextra": {"shift": 0,
                              "KekuleNo": ""},

            "ancestorpaternal": False,
            "ancestormaternal": False,

            "proband": {"enable": False,
                         "color": False,
                         "images": {"enable": False, "exist": False, "onside": True},
                        },
            "probandspouse": {"enable": False,
                              "color": False,
                              "images": {"enable": False, "exist": False, "onside": True}
                             },
            "probandspouseparents": {"enable": False,
                              "color": False,
                              "images": {"enable": False, "exist": False, "onside": True}
                             },
            "probandfamily": {"enable": False,
                              "color": False,
                              "civil": False, "church": False, "line": False,
                              "childscount": False
                             },

            "descendant": {"enable": False,
                           "color": False,
                           "uncolorlist": [],
                           "images": {"enable": False, "exist": False, "onside": True},
                          },
            "descendantspouse": {"enable": False,
                                 "color": False,
                                 "uncolorlist": [],
                                 "images": {"enable": False, "exist": False, "onside": True}
                                },
            "descendantspouseparents": {"enable": False,
                                 "color": False,
                                 "uncolorlist": [],
                                 "images": {"enable": False, "exist": False, "onside": True}
                                },
            "descendantfamily": {"enable": False,
                                 "color": False,
                                 "civil": False, "church": False, "line": False,
                                 "childscount": False
                                },
            "descendantextra": {"shift": 0,
                                "HenryNo": ""},
            "descendantfamilyextra": {"enable": False},

            "descendantpaternal": False,
            "descendantmaternal": False,
            "descendantnamelist": []
        }

        self.color = {}
        self._color = {
            "base": Color(),
            "ancestor": {
                "uncolorlist" : []
            },
            "proband": {
                "uncolorlist" : []
            },
            "descendant": {
                "uncolorlist" : []
            },

            "add-name": {},
            "add-person": {},
            "add-family": {},
            "add-paternal": {},
            "add-maternal": {},
            "add-xdnaoptXX": {},
            "add-xdnaoptXY": {},

            "levelcolor": False,
            "gradientcolor": False,
            "degreecolor": {
                "enable": False,
                "male": {"style": "striped", "fillcolor": "#0000FF"},
                "female": {"style": "wedged", "fillcolor": "#FF0000"},
                "descendant": {"fillcolor": "#D3D3D3"}
            },

            "shiftgeneration": 0,
            "reversegeneration": False,

            "scheme": "",
            "threshold": 127.5,
        }

        # Pathes
        self.pathes = {
            "enable": False   # korrekt!
        }
        self._pathes = {
            "searchtool": "NX",
            "spouse": False,

            "sources": "",
            "targets": "",
            "edges": {},

            "node": {
              "rotate": [],
            },
            "edge": {
                "male": {"fontcolor": "#000000"},
                "female": {"fontcolor": "#000000"},
                "labelspace": {},
            },
        }

        # Hyphenation (of Names)
        self.hyphenation = {
            "enable": False
        }

        # Implex
        self.implex = {}
        self._implex = {
            "calculation": {
                "enable": False,
                "searchtool": "GT",
                "searchset": "All",

                "spouse": False,
                "cyclelist": ["All"],
                "uncyclelist": [],
            },

            "male": {
                "id": "I00000",
                "shape": "square", "style": "filled",
                "bordercolor": "#000000", "fillcolor": "#0000FF", "fontcolor": "#000000"
            },
            "female": {
                "id": "I00000",
                "shape": "circle", "style": "filled",
                "bordercolor": "#000000", "fillcolor": "#FF0000", "fontcolor": "#000000"
            },
            "family": {
                "debug": 0,   # shows invisible 1: nodes, 2: edges, 3: nodes+edges
            },
            "node": {
            },
            "edge": {
                "label": True,
                "spacer": True,
            },

            "cluster": {
                "debug": False,   # Test Boundingbox
                "FID": [],   # Familien-Cluster
            },
            "pathes": {"enable": False,
                "time": {},
                "ident_bordercolor": "#000000",
            },
            "cycles": {
                "enable": False,
            },
            "xlabel": {
                "enable": False,
            },
            "additional": {
                "PedigreeCollapse": {
                    "enable": False,
                    "pidlist": [],
                },
            },
        }

        self.diagram = {}
        self._diagram = {
            "attributes": {
                "EoL": {"enable": False},   # Spitzenahnen (EndOfLine)
            },
            "ids": {"style": 2,   # 0: null -, 1: same -, 2: own Line
                "markstart": "[", "markstop": "]"
            },
            "names": "shortname",   # "none", "briefname", "shortname", "surname"
            "number": {
                "KekuleNo": False, "HenryNo": False,
                "markstart": "", "markstop": ""
            },
            "dates": {"enable": True, "onlyyears": True},
            "places": {"enable": True, "extended": False, "images": False},
            "images": {"enable": False, "exist": False}
        }

        self.dot = {}
        self._dot = {
            "dpi": 600,
            "bgcolor": "white",   # white, transparent
            "concentrate": True,
            "ratio": "compress",
            "sizew": "14.0",
            "sizeh": "5.0",
            "font": {
              "family": "Liberation Sans Narrow:Regular",
              "size": 12,
              "extra": "fixedsize=true"
            },
            "rankdir": "TB",   # Top-Bottom, Bottom-Top
            "nodesep": 0.1,   # Horizontal distance between nodes (default: 0.1)
            "ranksep": 0.1,   # Vertical distance between nodes (default: 0.5)
            "splines": "spline",   # "Line", "ortho", "polyline", "splines"
        }
        self.node = {}
        self._node = {
            "rank": False,
            "default": {"shape": "box", "style": "rounded, filled",
                        "height": 0.1, "width": 0.1, "margin": 0.05,
                        "bordercolor": "#000000", "fillcolor": "#D3D3D3", "fontcolor": "#000000"},
            "person": {
                "male": {
                  "shape": "box", "style": "rounded, filled",
                  "bordercolor": "#000A66", "fillcolor": "#E0E0FF",
                  "height": 0.1, "width": 0.1, "margin": 0.05,
                },
                "female": {
                  "shape": "box", "style": "rounded, filled",
                  "bordercolor": "#660000", "fillcolor": "#FFE0E0",
                  "height": 0.1, "width": 0.1, "margin": 0.05,
                },
                "spacer": {},
                "style": "solid",
                "fontsize": 10,
                "penwidth": 2
            },
            "family": {
                "rank": False,
                "shape": "ellipse", "style": "filled",
                "bordercolor": "#000000", "fillcolor": "#FFFFCC"
            }
        }
        self.edge = {}
        self._edge = {
            "arrowheadstyle": "normal",
            "arrowtailstyle": "none",
            "minlen": 2
        }

    def read_dataset(self, options):
        """"""
        def update(d, u):
            for k, v in u.items():
                if isinstance(v, collections.abc.Mapping):
                    d[k] = update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        if 'data_set' in options.options_dict:
            file_name = options.options_dict['data_set']
            if file_name[-3:] != ".js": file_name += ".js"
            with open(file_name, 'r') as self.data_handle:
                dataset = json.load(self.data_handle)

        {setattr(self, key, value) for (key, value) in dataset.items()}

        self.base  = {**self._base,  **self.base}
        if not self.base['path']:
            raise ReportError(_('No base path'), _('You have to define a base path'))
        if not self.base['sourcefile']:
            raise ReportError(_('No sourcefile'), _('You have to define a filename'))
        else: self.base['sourcefile'] = self.base['path'] + '/' + self.base['sourcefile']
        if not self.base['targetfile']:
            raise ReportError(_('No targetfile'), _('You have to define a filename'))
        else: self.base['targetfile'] = self.base['path'] + '/' + self.base['targetfile']
        if keys_true(self.base, 'analyzefile'):
            self.base['analyzefile'] = self.base['path'] + '/' + self.base['analyzefile']
        if keys_true(self.base, 'addendumfile'):
            self.base['addendumfile'] = self.base['path'] + '/' + self.base['addendumfile']
        options.set_output(self.base['targetfile'])

        self.include = {**self._include,  **self.include}
        self.diagram = {**self._diagram,  **self.diagram}

        if 'pathes' in dataset:
            self.pathes = {**self._pathes, **self.pathes}
        if 'implex' in dataset:
            self.implex = {**self._implex, **self.implex}

        self.color = {**self._color,  **self.color}

        self.dot  = {**self._dot,  **self.dot}
        if 'note' in self.base:
            self.dot['note'] = self.base['note']
        if 'font' in self.dot:
            self.dot['fontfamily'] = self.dot['font']['family']
            self.dot['fontsize'] = self.dot['font']['size']
            if keys_exists(self.dot, 'font', 'extra'):
                self.dot['fontextra'] = self.dot['font']['extra']

        self.node = {**self._node, **self.node}
        self.edge = {**self._edge, **self.edge}

        return None

    def write_dataset(self, objekt, filename):
        """"""
        file_name = filename + '.json'
        with open(file_name, 'w') as file_handle:
            file_handle.write(json.dumps(objekt, indent=2))

    def begin_report(self):
        """
        Inherited method; called by report() in _ReportDialog.py

        This is where we'll do all of the work of figuring out who
        from the database is going to be output into the report
        """
        self._local_init()

        if not self.base["chart"].capitalize() in 'Board, Implex, Lineage':
            return

        if keys_true(self.base, 'analyzefile'):
            if self.base['analyzefile'][-4:] != ".txt": self.base['analyzefile'] += ".txt"
            self.analyze_handle = open(self.base['analyzefile'], 'w')
            self.analyze_handle.write("Start\n\n")

        # starting with the people of interest, we then add parents:
        if self.maxparents_generation > 0:
            print('Parents by Generation ...')
            self.find_parents_generation()

        # starting with the people of interest we add their children:
        if self.maxchildren_generation > 0:
            print('Children by Generation ...')
            self.find_children_generation()

        if self.maxgeneration > 0:
            print('Family by Generation ...')
            self.find_family_generation()

        if keys_true(self.base, 'addendumfile'):
            if self.base['addendumfile'][-4:] != ".add": self.base['addendumfile'] += ".add"
            self.addendum_handle = open(self.base['addendumfile'], 'w')
            self.addendum_handle.write("Start\n\n")

        self.local_node, self.local_path = False, False
        if self.pathes['enable']:
            print('Pathes by Generation ...')
            self.local_path = self.pathes
            if keys_exists(self.pathes, 'node'):
                self.local_node = self.pathes['node']
            if keys_exists(self.pathes, 'edge'):
                self.local_edge = self.pathes['edge']

            self.find_pathes(self.local_path)
            self.transfer_lineages(self.local_path)
            a = 1

        if self.base["chart"].capitalize() == 'Implex':
            print('Find Implex ...')
            if keys_exists(self.implex, 'pathes'):
                self.local_path = self.implex['pathes']
            if keys_exists(self.implex, 'node'):
                self.local_node = self.implex['node']
            if keys_exists(self.implex, 'edge'):
                self.local_edge = self.implex['edge']

            if self.implex['calculation']['enable']:
                self.calculate_cycles()

            if keys_exists(self.implex, 'extra'):
                extra_dict = self.apply_node_extra(self.implex['extra'])
                self.implex['Ind'].update(extra_dict)

            if keys_true(self.implex, 'pathes', 'enable'):
                self.find_pathes(self.local_path)
                self.transfer_lineages(self.local_path)
            if keys_true(self.implex, 'tags', 'enable'):
                self.add_tags()

        if keys_true(self.base, 'analyzefile'):
            self.analyze_handle.write("\nEnd\n")
            self.analyze_handle.close()
        if keys_true(self.base, 'addendumfile'):
            self.addendum_handle.write("\nEnd\n")
            self.addendum_handle.close()

    def write_report(self):
        """
        Inherited method; called by report() in _ReportDialog.py
        """
        print('Initialising ...')
        """
        self.doc.add_comment('# %s %d' % \
                             (self._('Number of people in database:'),
                              self.database.get_number_of_people()))
        self.doc.add_comment('# %s %d' %
                             (self._('Number of people of interest:'),
                              len(self.people)))
        self.doc.add_comment('# %s %d' %
                             (self._('Number of families in database:'),
                              self.database.get_number_of_families()))
        self.doc.add_comment('# %s %d' %
                             (self._('Number of families of interest:'),
                              len(self.families)))
        if self.removeextra:
            self.doc.add_comment('# %s %d' %
                                 (self._('Additional people removed:'),
                                  self.deleted_people))
            self.doc.add_comment('# %s %d' %
                                 (self._('Additional families removed:'),
                                  self.deleted_families))
        self.doc.add_comment('# %s' %
                             self._('Initial list of people of interest:'))
        """
        if self.base["chart"].capitalize() in 'Board, Implex, Lineage':
            for pid in self.interest_list:
                person = self.database.get_person_from_gramps_id(pid)
                name = person.get_primary_name().get_regular_name()

                # translators: needed for Arabic, ignore otherwise
                id_n = self._("%(str1)s, %(str2)s") % {'str1':pid, 'str2':name}
                self.doc.add_comment('# -> ' + id_n)

            print('Write Persons ...')
            self.write_persons()
            print('Write Families ...')
            self.write_families()
            print('Write Links ...')
            self.write_links()
            print('Write Dot- / PNG-Files ...')

        if self.base["chart"].capitalize() == 'Legend':
            self.add_legend()

    # ==========================================================================================================================

    def find_spouse_parents(self, spouse, generation):
        """"""
        for spouseparents_handle in spouse.get_parent_family_handle_list():
            spouseparents = self.database.get_family_from_handle(spouseparents_handle)
            if spouseparents:
                if spouseparents.gramps_id in self.include['unfidlist']: continue
                if not spouseparents.gramps_id in self.families:
                    self.families[spouseparents.gramps_id] = {}

                self.generation[spouseparents.gramps_id] = generation + 0.5
                self.families[spouseparents.gramps_id] = {'mode': 'N', 'type': 'SP', 'handle': spouseparents_handle}

                spousefather_handle = spouseparents.get_father_handle()
                if spousefather_handle:
                    spousefather = self.database.get_person_from_handle(spousefather_handle)
                    self.generation[spousefather.gramps_id] = generation
                    self.parents[spousefather.gramps_id] = {'type': 'SP', 'PID': spousefather.gramps_id,
                                         'KekuleNo': '', 'XDNA': {}, 'EoL': True,
                                         'spouse': False, 'handle': spousefather_handle}

                spousemother_handle = spouseparents.get_mother_handle()
                if spousemother_handle:
                    spousemother = self.database.get_person_from_handle(spousemother_handle)
                    self.generation[spousemother.gramps_id] = generation
                    self.parents[spousemother.gramps_id] = {'type': 'SP', 'PID': spousemother.gramps_id,
                                         'KekuleNo': '', 'XDNA': {}, 'EoL': True,
                                         'spouse': False, 'handle': spousemother_handle}

    def _apply_parents(self, handle, base, index):
        # if we have a limit on the generations of parents, and we've reached
        # that limit, then don't attempt to find any more ancestors
        if (not handle) or (index >= 2**(self.max_generation +1)):
            return

        person = self.database.get_person_from_handle(handle)
        ord_name = ordName(person)
        pid = person.get_gramps_id()
        if pid in self.uninterest_list:
            return

        # remember this generation!
        gen_no = self.shift_generation -int(math.log2(index))
        pc_str = 'PC' + str(abs(gen_no)).zfill(2)   # Pedigree Collapse
        if not (pc_str in self.generation):
            self.generation[pc_str] = 0
        # remember this person!
        self.generation[pid] = gen_no # lesser generation for Ancestors

        if pid == 'I07315':
            a = 1

        if pid not in self.parents:
            # print('People handle: %s' % type(handle))
            self.generation[pc_str] += 1
            self.parents[pid] = {'type': 'A', 'PID': pid,
                                 'KekuleNo': index, 'XDNA': {},
                                 'spouse': False, 'handle': handle}
            self.parents[pid]['base'] = base
            self.parents[pid]['EoL'] = False if 'N.N.' in ord_name.shortname else True
            nxG.add_node(person.gramps_id)
        else:
            if not keys_exists(self.parents[pid], 'KekuleNo'):
                self.parents[pid]['KekuleNo'] = index
            self.parents[pid]['EoL'] = False if 'N.N.' in ord_name.shortname else True

        if keys_exists(self.parents, pid):
            if self.include['descendantmaternal'] and base['gender'] == Person.FEMALE:
                if index in _FEMALEXX: self.parents[pid]['XDNA'] = {'type': 1, 'number': index}
                if index in _XDNAOPTX1: self.parents[pid]['XDNA'] = {'type': 3, 'number': index}
                if index in _XDNAOPTX2: self.parents[pid]['XDNA'] = {'type': 3, 'number': index}
            if self.include['descendantpaternal'] and base['gender'] == Person.MALE:
                if index in _MALEXY: self.parents[pid]['XDNA'] = {'type': 2, 'number': index}
                if index in _XDNAOPTX2: self.parents[pid]['XDNA'] = {'type': 4, 'number': index}

        # see if a family exists between this person and someone else
        # we have on our list of parents we're going to output -- if
        # there is a family, then remember it for when it comes time
        # to link spouses together
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            if family:
                family_id = family.gramps_id
                if family_id in self.include['unfidlist']: continue

                # Family between parents and children generation
                self.generation[family_id] = gen_no + 0.5

                # print('Family handle: %s' % type(family_handle))
                self.families[family_id] = {'mode': 'N', 'type': 'A', 'handle': family_handle}
                nxG.add_node(family.gramps_id)

                # include the spouse from this person's family
                spouse_handle = utils.find_spouse(person, family)
                if self.include['ancestorspouse']["enable"]  and spouse_handle:
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    spouse_id = spouse.get_gramps_id()
                    if spouse_id not in self.uninterest_list and \
                       spouse_id not in self.parents:
                        self.generation[pc_str] += 1
                        self.parents[spouse_id] = {'type': 'A', 'PID': spouse_id,
                                                   'handle': spouse_handle}
                        if index == 1:
                            self.parents[spouse_id]['type'] = 'P'

                        self.parents[spouse_id]['base'] = base
                        self.parents[spouse_id]['spouse'] = True \
                            if not self.parents[pid]['spouse'] else None
                        self.parents[spouse_id]['EoL'] = False if 'N.N.' in ord_name.shortname else True

                        self.generation[spouse_id] = gen_no
                        nxG.add_node(spouse.gramps_id)

                        if index == 1 and \
                           self.include['probandspouseparents']['enable']:
                            self.find_spouse_parents(spouse, gen_no -1)
                        if self.maxparents_generation <= gen_no -1 and \
                           self.include['ancestorspouseparents']['enable']:
                            self.find_spouse_parents(spouse, gen_no -1)

        # queue the parents of the person we're processing
        for family_handle in person.get_parent_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            if family:
                family_id = family.gramps_id
                if family_id in self.include['unfidlist']: continue

                # Family between parents and children generation
                self.generation[family_id] = gen_no + 0.5

                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()
                if father_handle or mother_handle:
                    self.parents[pid]['EoL'] = False   # Spitzenahnen (EndOfLine)
                if father_handle:
                    self._apply_parents(father_handle, base, index *2)
                if mother_handle:
                    self._apply_parents(mother_handle, base, (index *2) +1)

        return True

    def find_parents_generation(self):
        """ find the parents by generation """
        # we need to start with all of our "people of interest"
        self.ancestorsNotYetProcessed = set(self.interest_list)

        # now we find all the immediate ancestors of our people of interest
        self.max_generation = self.maxparents_generation
        # self.shift_generation = self.color['shiftgeneration']
        while self.ancestorsNotYetProcessed:
            key = self.ancestorsNotYetProcessed.pop()
            person = self.database.get_person_from_gramps_id(key)
            if person:
                base = {'pid': person.gramps_id, 'gender': person.gender}
                self._apply_parents(person.handle, base, 1)
                self.parents[key]['type'] = 'P'   # Proband

        for key, value in self.include['ancestorextra'].items():
            person = self.database.get_person_from_gramps_id(key)
            if person:
                base = {'pid': person.gramps_id, 'gender': person.gender}
                if 'shift' in value:
                    self.shift_generation = value["shift"]
                self._apply_parents(person.handle, base, value["index"])

        # merge temp set "parents" into master set
        self.parents = dict(sorted(self.parents.items()))
        self.people.update(self.parents)

        return True

    # --------------------------------------------------------------------------------------------------------------------------
    def _apply_children(self, generation, handle, gender, index, henryno):
        # if we have a limit on the generations of children, and we've reached
        # that limit, then don't attempt to find any more children
        if (not handle) or (generation > self.max_generation):
            return

        person = self.database.get_person_from_handle(handle)
        pid = person.get_gramps_id()
        if pid in self.include["unpidlist"]:
            return

        if pid == 'I13768':
            a = 1

        # remember this generation!
        gen_no = self.shift_generation + generation   # greater generation for descendants
        gen_str = 'G' + str(gen_no).zfill(2)
        if not (gen_str in self.generation):
            self.generation[gen_str] = 0

        # remember this person!
        default_VG = {'count': 0, 'generation': {}}   #  VG: Verwandtschaftsgrad
        if pid not in self.children:
            self.generation[gen_str] += 1
            self.generation[pid] = generation

            self.childrenCounter += 1
            child_data = {'type': 'D', 'HenryNo': [], 'XDNA': {}, 'VG': default_VG, 'spouse': False, 'handle': handle}
            child_data['HenryNo'].append(henryno)
            self.children[pid] = child_data

            nxG.add_node(pid)   # fill nxG nodes ...
        else:
            self.children[pid]['spouse'] = False
            if henryno not in self.children[pid]['HenryNo']:
                self.children[pid]['HenryNo'].append(henryno)
            if self.generation[pid] > generation:
                if keys_true(self.include['descendantextra'], pid, "shiftgeneration"):
                    pass # korrekt!
                else:
                    self.generation[pid] = generation

        if person.gender == gender:
            if self.include['descendantmaternal'] and gender == Person.FEMALE:
                self.children[pid]['XDNA'] = {'type': 1, 'number': index}
            if self.include['descendantpaternal'] and gender == Person.MALE:
                self.children[pid]['XDNA'] = {'type': 2, 'number': index}
        else:
            gender = -1

        # medium biological relationship
        count = 2**generation   #  2**n descendents
        if 'VG' not in self.children[pid]:   # VG: Verwandtschaftsgrad
            self.children[pid]['VG'] = default_VG
        self.children[pid]['VG']['count'] += 1 / count
        if generation not in self.children[pid]['VG']['generation']:
            self.children[pid]['VG']['generation'][generation] = 0
        self.children[pid]['VG']['generation'][generation] += 1

        # iterate through this person's families
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            family_id = family.gramps_id
            if family_id in self.include['unfidlist']: continue

            nxG.add_node(family_id)   # fill nxG nodes ...
            nxG.add_edge(pid, family_id)   # fill nxG edges ...

            # Family between parents and children generation
            self.generation[family_id] = gen_no + 0.5

            #  include only if generation < maxspouse_generation
            if self.maxspouse_generation > 0:
                if generation -1 > self.maxspouse_generation:
                    continue

            # include only when parents in descendantnamelist
            if self.include['descendantnamelist']:   # only Persons in descendantNameList!
                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()
                if father_handle:
                    father = self.database.get_person_from_handle(father_handle)
                    father_name = father.get_primary_name().get_primary_surname().surname
                if mother_handle:
                    mother = self.database.get_person_from_handle(mother_handle)
                    mother_name = mother.get_primary_name().get_primary_surname().surname
                if (father_handle and father_name not in self.include['descendantnamelist']) and \
                   (mother_handle and mother_name not in self.include['descendantnamelist']):
                    continue

            # include the spouse from this person's family
            spouse_handle = utils.find_spouse(person, family)
            if self.include['descendantspouse']["enable"] and spouse_handle:
                spouse = self.database.get_person_from_handle(spouse_handle)
                spouse_id = spouse.get_gramps_id()
                if spouse_id in self.uninterest_list:
                    continue

                nxG.add_node(spouse_id)   # fill nxG nodes ...
                nxG.add_edge(spouse_id, family_id)   # fill nxG edges ...

                if spouse_id not in self.children:
                    self.children[spouse_id] = {'type': 'D', 'HenryNo': [], 'spouse': True, 'handle': spouse_handle}
                    self.generation[spouse_id] = gen_no

                    if family_id not in self.families:
                        self.families[family_id ] = {'mode': 'N', 'type': 'D', 'handle': family_handle}

                    if self.maxchildren_generation <= gen_no and \
                       self.include['descendantspouseparents']['enable']:
                        self.find_spouse_parents(spouse, gen_no -1)

            # queue up any children from this person's family
            idx = 0
            for child_ref in family.get_child_ref_list():
                child = self.database.get_person_from_handle(child_ref.ref)
                child_id = child.get_gramps_id()
                if child_id in self.no_descendant_list:
                    continue

                nxG.add_node(child_id)   # fill nxG nodes
                nxG.add_edge(family_id, child_id)   # fill nxG edges ...

                if self.include['descendantfamily']['enable']:
                    if family_id not in self.families:
                        self.families[family_id] = {'mode': 'N', 'type': 'D', 'handle': family_handle}

                self._apply_children(generation +1, child_ref.ref, gender, self.childrenCounter, henryno + _HENRY[idx])
                idx += 1

        return None

    def find_children_generation(self):
        """ find any children by generation """
        # we need to start with all of our "people of interest"
        self.childrenNotYetProcessed = set(self.interest_list)

        # now we find all the children of our people of interest
        self.max_generation = self.maxchildren_generation
        # self.shift_generation = self.color['shiftgeneration']
        self.childrenCounter = 0
        while len(self.childrenNotYetProcessed) > 0:
            key = self.childrenNotYetProcessed.pop()
            person = self.database.get_person_from_gramps_id(key)
            if person:
                self._apply_children(0, person.handle, person.gender, 0, '1')
                self.children[key]['type'] = 'P'   # Proband

        for key, value in self.include['descendantextra'].items():
            person = self.database.get_person_from_gramps_id(key)
            if person:
                if 'HenryNo' in value:
                    self.children[key]['HenryNo'].append(value['HenryNo'])

        # merge temp set "children" into our master set
        self.people.update(self.children)
        if self.include['descendantspouseparents']['enable']:
            self.people.update(self.parents)

        analyze_list = []
        for key, value in self.generation.items():
            if not key.startswith('G'): continue
            if key in _GENERATIONNAME_:
                print('  %s: %s Persons' % (_GENERATIONNAME_[key], value))
                analyze_list.append('%s: %s Persons\n' % (_GENERATIONNAME_[key], value))

        print('  Summary: %d' % len(self.children))
        analyze_list.append('Summary: %d\n' % len(self.children))

        if keys_exists(self.base, 'analyzefile') and self.base['analyzefile']:
            for analyze in analyze_list: self.analyze_handle.write(analyze)

    def find_family_generation(self):
        """ find any family by generation """

        # create property 'gen' on highest level
        # nxG['gen'] = 0

        # link parents and children to families
        for key, value in self.families.items():

            # get the parents for this family
            family = self.database.get_family_from_gramps_id(key)
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()

            # see if we have a father to link to this family
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                father_id = father.get_gramps_id()
                if father_id in self.people:
                    nxG.add_edge(father_id, key)
                    gen = abs(self.generation[father_id])
                    nxG[father_id][key]['gen'] = gen

            # see if we have a mother to link to this family
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                mother_id = mother.get_gramps_id()
                if mother_id in self.people:
                    nxG.add_edge(mother_id, key)
                    gen = abs(self.generation[mother_id])
                    nxG[mother_id][key]['gen'] = gen

            # link the children to the family
            for childref in family.get_child_ref_list():
                child = self.database.get_person_from_handle(childref.ref)
                child_id = child.get_gramps_id()
                if child_id in self.people:
                    nxG.add_edge(key, child_id)
                    gen = abs(self.generation[child_id])
                    nxG.nodes[key]['gen'] = gen +0.5
                    nxG[key][child_id]['gen'] = gen

            # sort the families into rank
            if 'rank' in self.node and self.node['rank']:
                if isinstance(self.node['rank'], bool): self.node['rank'] = {}
                gen = self.generation[key]
                if gen not in self.node['rank']:
                    self.node['rank'][gen] = []
                    self.node['rank'][gen].append(key)
                else:
                    if key not in self.node['rank']:
                        self.node['rank'][gen].append(key)

        print('  Families: %d' % len(self.families))

        if keys_true(self.base, 'analyzefile'):
            self.analyze_handle.write('Families: %d\n\n' % len(self.families))

        # find target node(s)
        """ Alternative
        for tidchildren in self.targetlist.split():
            targetnode = [handle for handle, attr in nxG.nodes(data=True) if attr['id'] == tid]
            if targetnode: self.targetnodes.append(targetnode[0])
        """

    # --------------------------------------------------------------------------------------------------------------------------
    def find_pathes(self, pathes):
        """"""
        debug = False

        if pathes['searchtool'] == 'GT':
            print('  GT: All Paths', end = '', flush=True)
        if pathes['searchtool'] == 'NX':
            print('  NX: Simple Edge Paths', flush=True)

        for path in list(pathes):
            if not path.startswith('path'): continue

            if 'source_id' in pathes[path] and isinstance(pathes[path]['source_id'], list):
                for source in list(pathes[path]['source_id']):
                    temp_path = copy.deepcopy(pathes[path])
                    temp_path['source_id'] = source
                    pathes[source] = temp_path
                if path in pathes: del pathes[path]

            target_id, target_nr = "", ''
            if 'target_id' in pathes[path] and isinstance(pathes[path]['target_id'], list):
                for target in list(pathes[path]['target_id']):
                    temp_path = copy.deepcopy(pathes[path])
                    temp_path['target_id'] = target
                    target_id = target
                    if target_id in pathes:
                        target_nr = chr(ord(target_nr) +1) if target_nr else 'a'
                        target_id = '%s%s' % (target, target_nr)
                    pathes[target_id] = temp_path
                if path in pathes: del pathes[path]

        path_num = 0
        for path in list(pathes):
            if not (path.startswith('path') or path.startswith('I') or path.startswith('F')):
                continue
            if not (pathes[path]['source_id'] and pathes[path]['target_id']) in nxG:
                continue

            path_num += 1
            pathes['time'] = {}
            pathes['time']['begin'] = datetime.datetime.now()

            time_actual = datetime.datetime.now()

            # Graph-Tool -----------------------------------------------------------------------
            if pathes['searchtool'] == 'GT':
                self.lineages['nx2gt'], self.lineages['gt2nx'] = {}, {}

                gtG = nx2gt(nxG)   # transfer NetworkX data to GraphTool data
                # gtG.list_properties()

                for i in range(gtG.num_vertices()):   # fill Property (= Gramps-ID) lookup tables
                    key = gtG.vertex_properties['id'][i]
                    self.lineages['nx2gt'][key] = i
                    self.lineages['gt2nx'][i] = key

                source, target = pathes[path]['source_id'], pathes[path]['target_id']
                # source_vertex = find_vertex(gtG, gtG.vp['id'], source)[0]   # from graph_tool.util
                source_vertex = self.lineages['nx2gt'][source]
                # target_vertex = find_vertex(gtG, gtG.vp['id'], target)[0]   # from graph_tool.util
                target_vertex = self.lineages['nx2gt'][target]

                # compute number of shortest paths (from graph_tool.topology)
                # pathsGT_num = count_shortest_paths(gtG, source=source_vertex, target=target_vertex, \
                #                                   weights=gtG.edge_properties["gen"])

                # compute shortest path (from graph_tool.topology)
                pathsGT = shortest_path(gtG, source=source_vertex, target=target_vertex, \
                                        weights=gtG.edge_properties["gen"])
                pathsGT_len = len(pathsGT[0])   # Number of vertexes in shortes path
                if self.cutoffpath > pathsGT_len:
                    self.cutoffpath = pathsGT_len + 1
                # pathsGT = all_shortest_paths(gtG, source=source_vertex, target=target_vertex, \
                #                             weights=gtG.edge_properties["gen"])

                # compute >all< paths (from graph_tool.topology)
                pathsGT = all_paths(gtG, source=source_vertex, target=target_vertex, \
                                    cutoff=self.cutoffpath, edges=True)

                # transfer Graph Tool path to common structure
                edgeGT = []   # local edge list
                for p_num, p in enumerate(pathsGT):
                    edgeGT.append([])

                    for e in p:
                        # mapping edge souce / target (= vertexes) indices via int() to Gramps-IDs
                        line = [self.lineages['gt2nx'][int(e.source())], self.lineages['gt2nx'][int(e.target())]]
                        edgeGT[p_num].append(line)

                    if p_num > 0: print(end=', ', flush=True)
                    time_elapsed = (datetime.datetime.now() - time_actual).total_seconds()
                    # print('%d (%4.2f sec.)' % (p_num +1, time_elapsed), end='', flush=True)
                    time_actual = datetime.datetime.now()

                    if 'max_pathes' in path and (path['max_pathes'] == p_num +1):
                        break   # only defined amount of pathes

                if not edgeGT:
                    continue

                pathes[path][path_num] = edgeGT

            # NetworkX -------------------------------------------------------------------------
            if pathes['searchtool'] == 'NX':
                edgeNX = []   # local edge list
                try:
                    edgeNX = list(nx.all_simple_edge_paths(nxG, \
                        source=pathes[path]['source_id'], target=pathes[path]['target_id'], \
                        cutoff=self.cutoffpath))
                except nx.NodeNotFound:
                    print('  Node(s) not found: %s -> %s' % (pathes[path]['source_id'], pathes[path]['target_id']))
                    if self.base['analyzefile']:
                        self.analyze_handle.write('\nNode(s) not found: %s -> %s' % (pathes[path]['source_id'], pathes[path]['target_id']))

                if not edgeNX:
                    continue

                pathes[path][path_num] = edgeNX

            # Test if generation are first strictly increasing then strictly decreasing
            for edge_num, edge in enumerate(list(pathes[path][path_num])):
                data_list = list(itertools.chain.from_iterable(edge))
                gen_list, gen_rank = self.calculate_ranks(data_list)
                max_value = max(gen_list)
                apx_index = gen_list.index(max_value)

                inc_list, dec_list = gen_list[:apx_index], gen_list[apx_index:]
                if not(inc_list == sorted(inc_list)): # and dec_list == sorted(dec_list, reverse=True)
                    del(pathes[path][path_num][edge_num])
                    path_information = 'Path not strictly increasing/decreasing (monoton)'
                    print("  %d. Path (%d) -> %s" % (path_num, len(data_list), path_information))

            # Test if path in UnPathList
            if path_num in self.pathes['unpathlist']:
                if pathes[path][path_num]:
                    del(pathes[path][path_num])
                path_information = 'Path in UnPathList'
                print("  %d. Path (%d) -> %s" % (path_num, len(pathes[path]), path_information))

            # Done -----------------------------------------------------------------------------
            pathes['time']['calc'] = (datetime.datetime.now() - pathes['time']['begin']).total_seconds()
            if debug:
                print("\n  Calc. time: %0.2f sec." % pathes['time']['calc'])

            # Success? -------------------------------------------------------------------------
            # if not pathes[path][path_num]:
            #    del pathes[path][path_num]
            #    continue

        if path_num:
            print('Process. Pathes: %d' % path_num)

        return None

    def transfer_lineages(self, pathes):
        """"""
        debug = False
        def find_spouse(person, person_lineage):
            """"""
            # iterate through this person's families
            for family_handle in person.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)
                family_id = family.gramps_id
                if family_id in self.include['unfidlist']: continue

                # include the spouse from this person's family
                spouse_handle = utils.find_spouse(person, family)
                if spouse_handle:
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    spouse_id = spouse.get_gramps_id()
                    if spouse_id in self.uninterest_list:
                        continue

                    person_lineage[spouse_id] = {'pid': spouse.gramps_id}

        def update_color(color_id, color_key, color_width):
            """"""
            lineage = {}
            if not color_id: return lineage

            hex_color = color_key
            rgb_color = self.color['base'].HEXtoRGB(hex_color)
            '''
            generation = int(source.pop(0).split('=')[1])
            # cie_color = self.color['base'].BACKGROUND[self.color["scheme"]][generation]
            # lab_color = self.color['base'].CMYKtoLAB(cie_color['CMYK'])
            lab_color = self.color['base'].BACKGROUND[self.color["scheme"]][generation]['Lab']
            lab_color[0] -= 25   # -> L* += 25
            hex_color = self.color['base'].LABtoHEX(lab_color)
            '''
            label_color = '#000000' if self.color['base'].isLight(rgb_color, self.color["threshold"]) else '#FFFFFF'

            lineage['ID'] = color_id
            lineage['fontcolor'] = label_color
            lineage['fillcolor'] = hex_color
            lineage['penwidth'] = color_width

            return lineage

        self.lineages['Edges'] = {}
        self.lineages['Sources'], self.lineages['Targets'] = [], []
        self.lineages['Ind'], self.lineages['Fam'] = {}, {}

        # Transfer ---------------------------------------------------------------------------------------------------------
        pathes['time'] = {}
        pathes['time']['begin'] = datetime.datetime.now()   # Transfer-Time

        path_num = 0
        for path in pathes:
            if not (path.startswith('path') or path.startswith('I') or path.startswith('F')):
                continue

            path_num += 1
            if keys_exists(pathes, path, 'source_color'):   # no colors for Implex:XLabel:Pathes
                lineage = update_color(pathes[path]['source_id'], pathes[path]['source_color'], pathes[path]['source_width'])
                self.lineages['Sources'].append(lineage)

            if keys_exists(pathes, path, 'target_color'):   # no colors for Implex:XLabel:Pathes
                lineage = update_color(pathes[path]['target_id'], pathes[path]['target_color'], pathes[path]['target_width'])
                self.lineages['Targets'].append(lineage)

            if debug:
                print("  Lineage -> ", end='', flush=True)

            for track_num, track in enumerate(pathes[path]):
                if isinstance(track, str): continue

                analyze_list = []
                person_lineage, family_lineage, edge_lineage = {}, {}, {}

                if debug and track_num > 0: print(end=', ', flush=True)
                try:
                    if self.base['analyzefile']:
                        analyze_list.append("\n--> %d. Path\n" % path_num)

                    for line_num, line in enumerate(pathes[path][track]):
                        # if line_num > 0: continue

                        if len(pathes[path][track]) > 1:
                            analyze_list.append("    %d. Track\n" % (line_num +1))

                        for edge_num, edge in enumerate(line):
                            key = '%s-%s' % (edge[0], edge[1])
                            if key not in self.lineages['Edges']:
                                edge_lineage[key] = \
                                    [path, pathes[path]['edge_style'], pathes[path]['edge_color'], \
                                     pathes[path]['edge_width']]

                            if edge[0].startswith('I'):
                                person = self.database.get_person_from_gramps_id(edge[0])

                                if edge[0] not in self.lineages['Ind'] and edge[0] not in person_lineage:
                                    person = self.database.get_person_from_gramps_id(edge[0])
                                    person_lineage[edge[0]] = {'pid': person.gramps_id}
                                    # if keys_exists(self.pathes, 'node', 'HenryNo'):
                                    #    person_lineage[edge[0]]['HenryNo'] = self.people[edge[0]]['HenryNo']
                                    if keys_exists(self.pathes, 'spouse'):
                                        find_spouse(person, person_lineage)

                                if edge[1] not in self.lineages['Fam'] and edge[1] not in family_lineage:
                                    family = self.database.get_family_from_gramps_id(edge[1])
                                    family_lineage[edge[1]] = {'type': 'D', 'fid': family.gramps_id}
                                if self.base['analyzefile']:
                                    ord_name = ordName(person)
                                    analyze_list.append('%2d. %5s %s\n' % (edge_num +1, edge[0], ord_name.shortname))

                            if edge[0].startswith('F'):
                                person = self.database.get_person_from_gramps_id(edge[1])
                                family = self.database.get_family_from_gramps_id(edge[0])
                                father_handle = family.get_father_handle()
                                mother_handle = family.get_mother_handle()

                                if edge[0] not in self.lineages['Fam'] and edge[0] not in family_lineage:
                                    family = self.database.get_family_from_gramps_id(edge[0])
                                    family_lineage[edge[0]] = {'type': 'D', 'fid': family.gramps_id}
                                if edge[1] not in self.lineages['Ind'] and edge[1] not in person_lineage:
                                    person = self.database.get_person_from_gramps_id(edge[1])
                                    person_lineage[edge[1]] = {'pid': person.gramps_id}
                                    # if keys_exists(self.pathes, 'node', 'HenryNo'):
                                    #    person_lineage[edge[1]]['HenryNo'] = self.people[edge[1]]['HenryNo']
                                    if self.local_path and keys_exists(self.local_path, 'spouse'):
                                        find_spouse(person, person_lineage)

                                if self.base['analyzefile']:
                                    father_name, mother_name = '', ''
                                    if father_handle:
                                        father = self.database.get_person_from_handle(father_handle)
                                        father_name = father.get_primary_name().get_primary_surname().surname
                                    if mother_handle:
                                        mother = self.database.get_person_from_handle(mother_handle)
                                        mother_name = mother.get_primary_name().get_primary_surname().surname
                                    family_name = '%s -- %s' % (father_name, mother_name)
                                    analyze_list.append('%2d. %5s %s\n' % (edge_num +1, edge[0], family_name))

                except StopIteration:
                    print("(%d)" % (track_num +1), end='', flush=True)
                else:
                    self.lineages['Edges'].update(edge_lineage)
                    self.lineages['Ind'].update(person_lineage)
                    self.lineages['Fam'].update(family_lineage)
                    if self.base['analyzefile']:
                        for analyze in analyze_list:
                            self.analyze_handle.write(analyze)

                    if debug:
                        print("%d" % (track_num +1), end='', flush=True)

            pathes['time']['trans'] = (datetime.datetime.now() - pathes['time']['begin']).total_seconds()
            if debug:
                print('\nCalc. Pathes: %d' % (track_num +1))
                print('Accept. Pathes: %d' % (path_num))
                print("Transfer time: %0.2f sec." % pathes['time']['trans'])
                # self.doc.note.append('Calc. Pathes: %d' % lineage_num)

        if path_num:
            print('Process. Lineages: %d' % path_num)
            pathes['time']['end'] = datetime.datetime.now()
            pathes['time']['elapsed'] = (pathes['time']['end'] - pathes['time']['begin']).total_seconds() / 60.0
            print("Elaspsed time: %0.2f min." % pathes['time']['elapsed'])

        self.lineages['source_set'], self.lineages['target_set'] = set(), set()
        for source in self.lineages['Sources']: self.lineages['source_set'].add(source['ID'])
        for target in self.lineages['Targets']: self.lineages['target_set'].add(target['ID'])

        return None

    # --------------------------------------------------------------------------------------------------------------------------
    def add_tags(self):
        """"""
        self._debug_ = False

        all_tags = {}
        for number, handle in enumerate(self.database.get_tag_handles(sort_handles=True)):
            tag = self.database.get_tag_from_handle(handle)
            tagnumber = 'tag' + str(number).zfill(2)
            all_tags[tagnumber] = {'name':  tag.get_name(), 'handle': tag.get_handle()}

        self.database.disable_signals()
        with DbTxn(_("Person tag creation"), self.database, batch=True) as self.trans:
            for handle in self.implex['Ind'].values():
                person = self.database.get_person_from_handle(handle)
                person.add_tag(all_tags['tag00']['handle'])

                if not self._debug_:
                    self.database.commit_person(person, self.trans)   # add & commit ...

        self.database.enable_signals()
        self.database.request_rebuild()

        return None

    def calculate_ranks(self, datalist):
        """"""
        gen_list, gen_rank = [], {}   # local rank
        for key in datalist:
            gen = self.generation[key]
            gen_list.append(gen)
            if not gen in gen_rank: gen_rank[gen] = 1
            else: gen_rank[gen] += 1

        return gen_list, gen_rank

    def calculate_cycles(self):
        """"""
        self.implex['result'] = {'to_short': [], 'to_long': [], 'no_searchset': [], 'equal_cycle': [], 'revers_cycle': [],
                                 'double_entries': [], 'not_monoton': [], 'cycle_list': [], 'uncycle_list': [], 'good': []}

        def spinning_cursor():
            while True:
                for cursor in '|/-\\':
                    yield cursor

        def transfer_graph_list(mode, graph_list):
            """"""
            cycle_count, start_count, good_count, short_count, long_count = 0, 5, 0, 0, 0
            start_time = datetime.datetime.now()
            for cycle_list in graph_list:
                cycle_count += 1
                if cycle_count > 1E8: break

                cycle_length = len(cycle_list)
                if (datetime.datetime.now() - start_time).seconds == 5:   # all 5 sec
                    print('  %2d. Sec: %7d Cycles (Good: %2s, Long: %7s, Short: %2s)' % \
                          (start_count, cycle_count, good_count, long_count, short_count))
                    start_count += 5
                    start_time = datetime.datetime.now()

                if cycle_length < self.implex['calculation']["minlength"] :   # min. length for a cycle
                    short_count += 1
                    # self.implex['result']['to_short'].append(cycle_count)
                    continue
                if cycle_length > self.maxchildren_generation *4 +1:   # max. length for a cycle
                    long_count += 1
                    # self.implex['result']['to_long'].append(cycle_count)
                    continue

                if mode == 'GT': cycle = [gt2nx[x] for x in cycle_list]
                if mode == 'NX': cycle = cycle_list

                self.implex['data'].append(cycle)
                good_count += 1
                # if good_count == 3: break

            # print('  processed: %d' % cycle_count)
            print('  Cycles: Good: %2s, Long: %7s, Short: %2s)' % (good_count, long_count, short_count))
            # (len(self.implex['result']['to_short']), len(self.implex['result']['to_long']))
            print('  Transfered: %d' % len(self.implex['data']))

            return True

        starttime = datetime.datetime.now()
        self.implex['Ind'] = {} # ID and handle of individuals we need in the report
        self.implex['Fam'] = {} # ID and handle of families we need in the report
        self.implex['data'] = []
        self.implex['circuits'] = {}

        # Graph-Tool -------------------------------------------------------------------------------------------------------
        if self.implex['calculation']["searchtool"] == 'GT':
            print('  GT: All Circuits ->\n', end='', flush=True)

            gtG = nx2gt(nxG)   # transfer NetworkX data to GraphTool data
            # gtG.list_properties()

            # fill Property (= Gramps-ID) lookup table
            gt2nx = dict((i, gtG.vertex_properties['id'][i]) for i in range(gtG.num_vertices()))

            # compute >all< circuits (from graph_tool.topology)
            implexGT = all_circuits(gtG, False)

            # transfer Graph Tool circuits to common structure
            transfer_graph_list('GT', implexGT)

        # IGraph -----------------------------------------------------------------------------------------------------------
        if self.implex['calculation']["searchtool"] == 'IG':
            print('  IG: All Cycle ->\n', end='', flush=True)

            igG = ig.Graph.from_networkx(nxG)   # transfer NetworkX data to IGraph data

        # NetworkX ---------------------------------------------------------------------------------------------------------
        if self.implex['calculation']["searchtool"] == 'NX':
            # only undirected Graphs ....
            """
            print('  NX: Cycle Basis ->\n', end='', flush=True)
            if self.implex["calculation"]["searchset"] != 'All' and \
               self.implex["calculation"]["searchset"] in nxG:
                implexNX = nx.cycle_basis(nxG, self.implex["calculation"]["searchset"])
            else:
                implexNX = nx.cycle_basis(nxG)
            """
            print('  NX: Simple Cycle ->\n', end='', flush=True)
            nxDG = nx.DiGraph(nxG)
            implexNX = sorted(nx.simple_cycles(nxDG))

            # transfer Graph Tool circuits to common structure
            print('  found: %d' % len(list(implexNX)))
            transfer_graph_list('NX', list(implexNX))

        #  -----------------------------------------------------------------------------------------------------------------

        endtime = datetime.datetime.now()
        if 'save' in self.implex['calculation'] and self.implex['calculation']["save"]:
            self.write_dataset(self.implex['data'], self.implex['calculation']["datafile"])
        print("  Elaspsed time: %0.2f min." % ((endtime - starttime).total_seconds() /60.0))

        # Test if cycle is double
        data_num, data_dict = 1, {}
        for data_idx, data_list in enumerate(list(self.implex['data'])):
            if all(x in ['I11857', 'F6003', 'I11974', 'F6062'] for x in data_list):
                a = 1
            if keys_exists(self.implex['calculation'], 'debug') and self.implex['calculation']['debug']:
                if not (data_idx +1) in self.implex['calculation']['debug']: continue

            # Test if cycle contains right! 'searchset'
            if 'All' not in self.implex['calculation']["searchset"]:
                if not any(ss in data_list for ss in self.implex['calculation']["searchset"]):
                    self.implex['result']['no_searchset'].append(str(data_idx))

                    data_information = 'Cycle did not! contains "searchset"'
                    print('  %d. Cycle (%d) -> %s' % (data_idx +1, len(data_list), data_information))
                    continue

            # Test if cycle equal another cycle
            if any([True for dt_dict in data_dict.values() \
                    if collections.Counter(dt_dict['list']) == collections.Counter(data_list)]):
                self.implex['result']['equal_cycle'].append(str(data_idx))

                data_information = "Cycle is equal to another cycle"
                print("  %d. Cycle (%d) -> %s" % (data_idx +1, len(data_list), data_information))
                continue

            # Test if cycle reversed equal another cycle
            if any([True for dt_dict in data_dict.values() \
                    if collections.Counter(list(reversed(dt_dict['list']))) == collections.Counter(data_list)]):
                self.implex['result']['revers_cycle'].append(str(data_idx))

                data_information = "Cycle is reversed equal to another cycle"
                print("  %d. Cycle (%d) -> %s" % (data_idx +1, len(data_list), data_information))
                continue

            # Test if cycle has double entries in one generation
            gen_list, gen_rank = self.calculate_ranks(data_list)
            if any([True for key, value in gen_rank.items() if value >= 4]):
                self.implex['result']['double_entries'].append(str(data_idx))

                cycle_information = 'Double entries in one generation'
                print("  %d. Cycle (%d) -> %s" % (data_idx +1, len(data_list), cycle_information))
                if keys_exists(self.implex['calculation'], 'debug') and not self.implex['calculation']['debug']: continue
                else: continue
            else:
                a = 1

            # Test if generation are first strictly increasing then strictly decreasing
            max_value = max(gen_list)
            apx_index = gen_list.index(max_value)

            inc_list, dec_list = gen_list[:apx_index], gen_list[apx_index:]
            if not(inc_list == sorted(inc_list) and dec_list == sorted(dec_list, reverse=True)):
                self.implex['result']['not_monoton'].append(str(data_idx))

                cycle_information = 'Cycle not strictly increasing/decreasing (monoton)'
                print("  %d. Cycle (%d) -> %s" % (data_idx +1, len(data_list), cycle_information))
                continue

            self.implex['result']['good'].append(str(data_idx))
            data_dict[data_num] = {'list': data_list, 'raw': data_idx, 'apex': apx_index}
            data_num += 1

        cycle_idx = 0   # necessary if data_dict == None!
        self.node['rank'] = {}   #  Activate Ranking!
        for cycle_idx, cycle_dict in enumerate(data_dict.values()):
            cycle_information = ''

            # Test if cycle in CycleList
            if not ('All' in self.implex['calculation']["cyclelist"]):
                if not((cycle_idx +1) in self.implex['calculation']["cyclelist"]):
                    self.implex['result']['cycle_list'].append(cycle_idx)

                    cycle_information = 'Cycle not in CycleList'
                    print("  %d. Cycle (%d) -> %s" % (cycle_idx +1, len(cycle_dict['list']), cycle_information))
                    continue

            # Test if cycle in UnCycleList
            if (cycle_idx +1) in self.implex['calculation']['uncyclelist']:
                self.implex['result']['uncycle_list'].append(str(cycle_idx +1))

                cycle_information = 'Cycle in UnCycleList'
                print("  %d. Cycle (%d) -> %s" % (cycle_idx +1, len(cycle_dict['list']), cycle_information))
                continue

            # Add global rank
            for key in cycle_dict['list']:
                gen = self.generation[key]
                if not gen in self.node['rank']:
                    self.node['rank'][gen] = []
                    self.node['rank'][gen].append(key)
                elif key not in self.node['rank'][gen]:
                    self.node['rank'][gen].append(key)

            label = ''
            cycle_key = 'cycle%02d' % (cycle_idx +1)
            if self.implex['xlabel']['enable'] and keys_exists(self.implex['xlabel']['sticker'], cycle_key):
                label = '%s ' % self.implex['xlabel']['sticker'][cycle_key]['label']
            if cycle_key in self.implex['cycles']:
                col_key = self.implex['cycles'][cycle_key]['color']
                line_key = self.implex['cycles'][cycle_key]['style']
            else:
                col_key = self.implex['cycles']['base']['color']
                line_key = self.implex['cycles']['base']['style']
            col_name = self.color['base'].IttenC5[col_key]['name']
            line_dict = {'solid': 'durchgezogen', 'dashed': 'unterbrochen', 'dotted':  'gepunktet'}
            line_name = line_dict[line_key]

            print("  %d. Cycle (%d)%s" % (cycle_idx +1, len(cycle_dict['list']), cycle_information))
            if self.base['analyzefile']:
                self.analyze_handle.write("--> %d. Implex %s(%d Elemente), Farbe: %s, Strichart: %s, RawIdx: %d\n" % \
                                          (cycle_idx +1, label, len(cycle_dict['list']) +1, col_name, line_name, \
                                          cycle_dict['raw']))
            if self.base['addendumfile']:
                self.addendum_handle.write("--> %d. Implex %s(%d Elemente), Farbe: %s, Strichart: %s\n" % \
                                          (cycle_idx +1, label, len(cycle_dict['list']) +1, col_name, line_name))

            father0_name, mother0_name, year0 = '', '', ''
            for item_num, item in enumerate(cycle_dict['list']):
                if item.startswith('I'):
                    person = self.database.get_person_from_gramps_id(item)
                    if person == None:
                        a = 1
                    pid = person.get_gramps_id()
                    if person:
                        # self.implex['Ind'][pid] = {'type': 'D', 'handle': person.get_handle()}
                        self.implex['Ind'][pid] = person.get_handle()

                        if self.base['analyzefile']:
                            person_name = get_name_from_gramps_id(self.database, pid)
                            date_options = {'endnote': False, 'year_only': True}
                            bdate, __ = determine_birthdate(self.database, person, date_options)
                            ddate, __ = determine_deathdate(self.database, person, date_options)
                            date_str = ''
                            if bdate or ddate:
                                date_str = '('
                                if bdate: date_str += '%s' % bdate
                                date_str += '–'
                                if ddate: date_str += '%s' % ddate
                                date_str += ')'

                            if item_num > 0:
                                if item_num <= cycle_dict['apex']:
                                    self.analyze_handle.write(' -> ')
                                    self.addendum_handle.write(' -> ')
                                else:
                                    self.analyze_handle.write(' <- ')
                                    self.addendum_handle.write(' <- ')
                            self.analyze_handle.write('%s %s (%.1f)' % (pid, person_name, self.generation[pid]))
                            self.addendum_handle.write(person_name)
                            if date_str:
                                self.addendum_handle.write(' %s' % date_str)

                if item.startswith('F'):
                    family = self.database.get_family_from_gramps_id(item)
                    family_id = family.get_gramps_id()
                    if family:
                        self.implex['Fam'][family_id] = {'type': 'D', 'handle': family.get_handle()}

                        father_handle = family.get_father_handle()
                        if father_handle:
                            father = self.database.get_person_from_handle(father_handle)
                            if father and father.gramps_id not in self.implex['Ind'] and self.implex['calculation']["spouse"]:
                                # self.implex['Ind'][father.gramps_id] = {'type': 'D', 'handle': father.get_handle()}
                                self.implex['Ind'][father.gramps_id] = father.get_handle()

                        mother_handle = family.get_mother_handle()
                        if mother_handle:
                            mother = self.database.get_person_from_handle(mother_handle)
                            if mother and mother.gramps_id not in self.implex['Ind'] and self.implex['calculation']["spouse"]:
                                # self.implex['Ind'][mother.gramps_id] = {'type': 'D', 'handle': mother.get_handle()}
                                self.implex['Ind'][mother.gramps_id] = mother.get_handle()

                if self.base['analyzefile']:
                    __, __, father_name, __, __, mother_name = get_name_from_gramps_id(self.database, family_id)
                    event, __ = find_specific_event \
                        (self.database, family, [EventType.CUSTOM, EventType.MARRIAGE], \
                         eventtyestring='Trauung', roletypelist=[EventRoleType.FAMILY])
                    year = event.date.get_year() if event else ''
                    if item_num == 0:
                        gramps0_id = family.gramps_id
                        generation0 = self.generation[family.gramps_id]
                        father0_name, mother0_name = father_name, mother_name
                        if year: year0 = year
                    else:
                        if item_num <= cycle_dict['apex']:
                            self.analyze_handle.write(' -> ')
                            self.addendum_handle.write(' -> ')
                        else:
                            self.analyze_handle.write(' <- ')
                            self.addendum_handle.write(' <- ')
                    self.analyze_handle.write('%s %s--%s (%.1f)' % \
                      (family.gramps_id, father_name, mother_name, self.generation[family.gramps_id]))
                    self.addendum_handle.write('%s -- %s' % (father_name, mother_name))
                    if year: self.addendum_handle.write(' (%s)' % year)

            #  -----------------------------------------------------------------------------------------------------------------

            cyc = list(zip(cycle_dict['list'], cycle_dict['list'][1:] + cycle_dict['list'][:1]))
            self.implex['circuits'][cycle_idx +1] = list('%s-%s' % (x, y) for x, y in cyc)

            #  -----------------------------------------------------------------------------------------------------------------
            if self.base['analyzefile']:
                self.analyze_handle.write(' <- ')
                self.analyze_handle.write('%s %s--%s (%.1f)' % \
                              (gramps0_id, father0_name, mother0_name, generation0))
                self.analyze_handle.write('\n\n')

            if self.base['addendumfile']:
                self.addendum_handle.write(' <- ')
                self.addendum_handle.write('%s -- %s' % (father0_name, mother0_name))
                if year0: self.addendum_handle.write(' (%s)' % year)
                self.addendum_handle.write('\n\n')

        if keys_true(self.implex, 'calculation', "save"):
            self.write_dataset(self.implex['Ind'], self.implex['calculation']["indfile"])
            self.write_dataset(self.implex['Fam'], self.implex['calculation']["famfile"])
            self.write_dataset(self.implex['circuits'], self.implex['calculation']["circutfile"])

            self.write_dataset(self.node['rank'], self.implex['calculation']["rankfile"])

        iplx_processed = cycle_idx +1 if cycle_idx else 0
        print('Implexes total: %d' % len(self.implex['data']))
        print('Implexes processed: %d' % iplx_processed)
        print('  Persons: %d' % len(self.implex['Ind']))
        print('  Families: %d' % len(self.implex['Fam']))

        if keys_true(self.base, 'analyzefile'):
            self.analyze_handle.write('Implexes total: %d\n' % len(self.implex['data']))
            self.analyze_handle.write('Implexes processed: %d\n' % iplx_processed)
            self.analyze_handle.write('  Persons: %d\n' % len(self.implex['Ind']))
            self.analyze_handle.write('  Families: %d\n\n' % len(self.implex['Fam']))

            for items in self.implex['result'].items():
                self.analyze_handle.write('%s: %s\n' % (items[0], len(items[1])))
                if not items[0].startswith('to'):
                    if items[1]: self.analyze_handle.write('[%s]\n' % ' '.join(items[1]))

        if keys_true(self.base, 'addendumfile'):
            self.addendum_handle.write('Implexes total: %d\n' % len(self.implex['data']))
            self.addendum_handle.write('Implexes processed: %d\n' % (cycle_idx +1))
            self.addendum_handle.write('  Persons: %d\n' % len(self.implex['Ind']))
            self.addendum_handle.write('  Families: %d\n' % len(self.implex['Fam']))

        return None

    # ==========================================================================================================================

    def update_node(self, source, target, mode=False):
        """"""
        if 'shape' in source and not target['shape']: target['shape'] = source['shape']
        if 'style' in source and not target['style']: target['style'] = source['style']
        if 'label' in source and not target['label']: target['label'] = source['label']

        if 'fontcolor' in source and (mode or not target['fontcolor']): target['fontcolor'] = source['fontcolor']
        if 'fillcolor' in source and (mode or not target['fillcolor']): target['fillcolor'] = source['fillcolor']
        if 'bordercolor' in source and not target['bordercolor']: target['bordercolor'] = source['bordercolor']

        if 'extension' in source and not target['extension']: target['extension'] = source['extension']

        if target['shape'] == 'point': target['label'] = ''

        return None

    def update_image_start(self, objekt, node):
        """"""
        # see if we have an image to use for this objekt
        if self.diagram['images']['enable']:
            image_path = ''
            media_list = objekt.get_media_list()
            if len(media_list) > 0:
                media_handle = media_list[0].get_reference_handle()
                media = self.database.get_media_from_handle(media_handle)
                media_mime_type = media.get_mime_type()
                if media_mime_type[0:5] == "image":
                    self.diagram['images']['exist'] = True
                    image_path = media_path_full(self.database, media.get_path())
                    """
                    image_path = get_thumbnail_path(
                        media_path_full(self.database, media.get_path()),
                        rectangle=media_list[0].get_rectangle(),
                        size=self.imagesize)
                    """

        # if we have an image, then start an HTML table;
        # remember to close the table afterwards!
        if image_path:
            node['label'] = ('<TABLE BORDER="0" CELLSPACING="2" CELLPADDING="0" '
                     'CELLBORDER="0"><TR><TD><IMG SRC="%s"/></TD>' % image_path)
            if self.diagram['images']['onside'] == 0:
                node['label'] += '</TR><TR>'
            node['label'] += '<TD>'
            node['htmloutput'] = True

    def update_image_stop(self, node):
        # see if we have a table that needs to be terminated
        if self.diagram['images']['exist']:
            node['label'] += '</TD></TR></TABLE>'
        else:
            # non html label is enclosed by "" so escape other "
            node['label'] = node['label'].replace('"', '\\\"')

    def include_levelcolor(self, generation, node):
        """"""
        rgb_color = (0, 0, 0)

        color_scheme = self.color['scheme']
        color_base = self.color['base'].BACKGROUND[color_scheme]
        color_number = len(color_base)

        gen = color_number - self.color['shiftgeneration'] - generation \
            if self.color['reversegeneration'] else self.color['shiftgeneration'] + abs(generation)
        if 'C1' in self.color["scheme"] or \
           'C3' in self.color["scheme"]:   # Itten xx ColorRing 1/3 (Inner/Middle)
            cymk_color = list(color_base[gen]['CMYK'])
            hex_color = self.color['base'].CMYKtoHEX(cymk_color)
            rgb_color = self.color['base'].HEXtoRGB(hex_color)
        elif 'C5' in self.color["scheme"]:   # Itten xx ColorRing 5 (Middle)
            rgb_color = list(color_base[gen]['RGB'])
            node['fillcolor'] = self.color['base'].RGBtoHEX(rgb_color)
        elif 'LabCMYK' in self.color["scheme"]:
            lab_color = list(color_base[gen])
            lab_color[0] += 0   # -> L* += 16
            rgb_color = self.color['base'].LABtoRGB(lab_color)
            node['fillcolor']= self.color['base'].LABtoHEX(lab_color)
        elif 'LabRGB' in self.color["scheme"]:
            rgb_color = list(color_base[gen])
            node['fillcolor'] = self.color['base'].RGBtoHEX(rgb_color)
        else:   # Standard Color
            rgb_color = (255, 255, 255)
        font_color = '#000000' if self.color['base'].isLight(rgb_color, self.color["threshold"]) else '#FFFFFF'

        node['fontcolor'] = font_color

    def include_gradientcolor(self, person, node):
        """"""
        ord_name = ordName(person)
        surname = ord_name.surname
        pid = person.gramps_id
        generation = self.generation[pid]

        if pid in self.generation and generation in self.generation.values():
            if generation < self.color["shiftgeneration"]:   # Ancestors
                if surname in self.color["ancestor"]:
                    node['fillcolor'], font_color = self.color["ancestor"][surname][0], self.color["ancestor"][surname][1]
                    if self.color["style"]["value"] > 0:
                        hls_list = list(self.color['base'].HEXtoHLS(node['fillcolor']))
                        lightness = hls_list[1] - self.color["style"]["value"]
                        hls_list[1] = lightness if lightness > 0.0 else 0.0
                        rgb_color = self.color['base'].HLStoRGB(tuple(hls_list))
                        font_color = '#000000' if self.color['base'].isLight(rgb_color, self.color["threshold"]) else '#FFFFFF'
                        node['fillcolor'] = self.color['base'].HLStoHEX(tuple(hls_list))
                    node['fontcolor'] = font_color
            if generation > self.color["shiftgeneration"]:   # Descendants
                if surname in self.color['descendant']:
                    node['fillcolor'], font_color = self.color['descendant'][surname][0], self.color['descendant'][surname][1]
                    if self.color["style"]["value"] > 0:
                        hls_list = list(self.color['base'].HEXtoHLS(node['fillcolor']))
                        lightness = hls_list[1] + self.color["style"]["value"]
                        hls_list[1] = lightness if lightness <= 1.0 else 1.0
                        rgb_color = self.color['base'].HLStoRGB(tuple(hls_list))
                        font_color = '#000000' if self.color['base'].isLight(rgb_color, self.color["threshold"]) else '#FFFFFF'
                        node['fillcolor'] = self.color['base'].HLStoHEX(tuple(hls_list))
                    node['fontcolor'] = font_color

    def include_degreecolor(self, person, node):
        """"""
        pid = person.gramps_id
        gender = person.gender
        if self.people[pid]['type'] != 'D':
            return False

        if keys_exists(self.people[pid], 'VG', 'count'):
            pweight = self.people[pid]['VG']['count'] /2
            rweight = 1.0 - pweight *2   # Restweight

            fillcolor = ''
            if pweight > 0.01:
                fillcolor += '%s;%.2f:' % (self.color['degreecolor']['male']['fillcolor'], pweight)
            if pweight > 0.01:
                fillcolor += '%s;%.2f:' % (self.color['degreecolor']['female']['fillcolor'], pweight)
            if rweight > 0.01:
                fillcolor += '%s;%.2f' % (self.color['degreecolor']['descendant']['fillcolor'], rweight) \
                    if node['fillcolor'] == '#FFFFFF' else '%s;%.2f' % (node['fillcolor'], rweight)
            node['fillcolor'] = fillcolor

            if gender == 0: node['style'] = self.color['degreecolor']['female']['style']
            if gender == 1: node['style'] = self.color['degreecolor']['male']['style']
            if rweight > 0.975: node['style'] = 'filled'
            # node['extension'] += ' gradientangle=%d' % 0 if gender == 1 else ' gradientangle=%d' % 90

            return True

    def include_xdnacolor(self, pid, node):
        """"""
        if self.include['descendantmaternal'] and self.people[pid]['XDNA']['type'] == 1:
            node['style'] = self.color['add-maternal']['style']
            node['fillcolor'] = self.color['add-maternal']['fillcolor']
            node['fontcolor'] = self.color['add-maternal']['fontcolor']
            node['extension'] += ' penwidth=%d' % self.color['add-maternal']['width']
        if self.include['descendantpaternal'] and self.people[pid]['XDNA']['type'] == 2:
            node['style'] = self.color['add-paternal']['style']
            node['fillcolor'] = self.color['add-paternal']['fillcolor']
            node['fontcolor'] = self.color['add-paternal']['fontcolor']
            node['extension'] += ' penwidth=%d' % self.color['add-paternal']['width']
        if self.include['descendantmaternal'] and self.people[pid]['XDNA']['type'] == 3:
            node['style'] = self.color['add-xdnaoptXX']['style']
            node['fillcolor'] = self.color['add-xdnaoptXX']['fillcolor']
            node['fontcolor'] = self.color['add-xdnaoptXX']['fontcolor']
            node['extension'] += ' penwidth=%d' % self.color['add-xdnaoptXX']['width']
        if self.include['descendantpaternal'] and self.people[pid]['XDNA']['type'] == 4:
            node['style'] = self.color['add-xdnaoptXY']['style']
            node['fillcolor'] = self.color['add-xdnaoptXY']['fillcolor']
            node['fontcolor'] = self.color['add-xdnaoptXY']['fontcolor']
            node['extension'] += ' penwidth=%d' % self.color['add-xdnaoptXY']['width']

        return True

    def include_individuallabel(self, person, node):
        """"""
        def apply_KekuleNo(node, pid, line_delimiter):
            # get the descendant number
            if node['label'] != '': node['label'] += line_delimiter
            if node['htmloutput']: node['label'] += self.diagram['number']['KekuleNo-markstart']

            # see if we have persons with additional informations
            if node['base']:
                bpid = self.people[pid]['base']['pid']
                color = self.color['ancestor'][bpid]['fontcolor']
            else:
                color = node['fontcolor']
            node['label'] = node['label'].replace('#xxxxxx', color)

            if keys_exists(self.include, 'add-person', 'KekuleNo') and pid in self.include['add-person']:
                node['label'] += "%s" % self.include['add-person'][pid]['KekuleNo']
            else:
                node['label'] += "%s" % self.people[pid]['KekuleNo'] #  %s!

            if node['htmloutput']: node['label'] += self.diagram['number']['KekuleNo-markstop']

        def apply_HenryNo(node, pid, line_delimiter):
            # get the descendant number
            henryno_list = []
            line_delimiter = ' &amp; '
            if (keys_true(self.include['descendantextra'], pid) and \
                not keys_true(self.include['descendantextra'], pid, 'sortHenryNo')):
                henryno_list = self.people[pid]['HenryNo']
            else:
                henryno_list = sorted(self.people[pid]['HenryNo'], key=len)
            for l, lbl in enumerate(henryno_list):
                if l > 0: node['label'] += line_delimiter
                if node['htmloutput']: node['label'] += self.diagram['number']['HenryNo-markstart']
                node['label'] += lbl
                if node['htmloutput']: node['label'] += self.diagram['number']['HenryNo-markstop']

        def get_date_place(event):
            date, place, unknown = '', '', False
            # get the date
            if self.diagram['dates']['enable']:
                date = event.get_date_object()
                if self.diagram['dates']['onlyyears'] and date.get_year_valid():   # localized year
                    date = self._get_date(Date(date.get_year()))
                else:
                    date = self._get_date(date)

            # get event place (one of: hamlet, village, town, city, parish,
            # county, province, region, state or country)
            if self.diagram['places']['enable']:
                place_type, place = get_event_place(self.database, event, True)
                if event.note_list:
                    event_notelist = event.get_note_list()
                    for handle in event_notelist:
                        note = self.database.get_note_from_handle(handle)
                        unknown |= 'not sure' in note.get_styledtext().string
                if place_type == 'Krankenhaus':
                    place = place.split(', ')[0] \
                        if self.diagram['places']['extended'] else place.split(', ')[1]

            return date, place, unknown

        # --------------------------------------------------------------------------------------
        pid = person.gramps_id
        ordname = ordName(person)
        briefname = ordname.briefname
        surname = ordname.surname

        if self.local_node and keys_exists(self.local_node, 'VG') and self.local_node['VG']['mode'] > 0:
            node['htmloutput'] = True
        line_delimiter = '' if self.diagram['names'] == 'noname' else '\\n'
        if node['htmloutput']: line_delimiter = '<BR/>'

        if self.base["chart"].capitalize() == 'Board' or \
           self.base["chart"].capitalize() == 'Lineage' or \
           self.base["chart"].capitalize() == 'Implex':
            name = briefname.replace('\n', '')
        # if self.base["chart"].capitalize() == 'Implex':
        #    name = briefname.replace('\n', line_delimiter)

        # Translation
        if self.translate_dict:
            lastname = '%s %s' % (ordname.prefix, ordname.lastname)
            if lastname in self.translate_dict['en']:
                ordname.set_composename(None, None, None,
                                        prefix=self.translate_dict['en'][lastname]['prefix'],
                                        lastname=self.translate_dict['en'][lastname]['lastname'])
            if self.diagram['names'] == 'briefname':
                name = ordname.briefname.replace('\n', line_delimiter)
            elif self.diagram['names'] == 'shortname':
                name = ordname.shortname

        # Trennungen (Hyphenation)
        if self.hyphenation['enable']:
            if self.diagram['names'] == 'briefname':
                if ordname.lastname in self.hyphenation:
                    ordname.set_composename(None, None, None, None, self.hyphenation[ordname.lastname])
                    name = ordname.briefname.replace('\n', line_delimiter)
                else: name = name.replace('-', '-' + line_delimiter)
            elif self.diagram['names'] == 'shortname':
                if ordname.lastname in self.hyphenation:
                    ordname.set_composename(None, None, None, None, self.hyphenation[ordname.lastname])
                    name = ordname.shortname
                else: name = ordname.shortname
            if self.diagram['names'] == 'surname':
                if surname in self.hyphenation: name = self.hyphenation[surname]
                else: name = surname.replace(' ', line_delimiter).replace('-', '-\n')

        birth_date, birth_place, birth_unknown = '', '', False
        death_date, death_place, death_unknown = '', '', False
        birth_event = get_birth_or_fallback(self.database, person)
        death_event = get_death_or_fallback(self.database, person)
        # output the birth or fallback event
        if birth_event and self.diagram['dates']['enable']:
            birth_date, birth_place, birth_unknown = get_date_place(birth_event)
        # output the birth or fallback event
        if death_event and self.diagram['dates']['enable']:
            death_date, death_place, death_unknown = get_date_place(death_event)

        # --------------------------------------------------------------------------------------
        # see if we have KekuleNo's
        if keys_true(self.diagram, 'number', 'KekuleNo') and keys_true(self.people[pid], 'KekuleNo'):
            apply_KekuleNo(node, pid, line_delimiter)
        # see if we have HenryNo's
        if keys_true(self.diagram, 'number', 'HenryNo') and keys_true(self.people[pid], 'HenryNo'):
            apply_HenryNo(node, pid, line_delimiter)

        if self.diagram['ids']['style'] == 2:   # IDs in own line
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += '%s[%s]%s' % \
                (self.diagram['ids']['markstart'], pid, self.diagram['ids']['markstop'])

        if self.diagram['names'].capitalize() != 'None':
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += name

        if self.diagram['ids']['style'] == 1:   # IDs in same line
            node['label'] += ' %s<SUB>[%s]</SUB>%s' % \
                (self.diagram['ids']['markstart'], pid, self.diagram['ids']['markstop'])

        birthsymbol, deathsymbol = '\u2217', '\u2020'
        if not self.diagram['images']['exist']:
            if node['label'] != '': node['label'] += line_delimiter
            if birth_date or death_date:
                node['label'] += '('
                if birth_date: node['label'] += '%s' % birth_date
                node['label'] += '–'
                if death_date: node['label'] += '%s' % death_date
                node['label'] += ')'

            if birth_place or death_place:
                if birth_unknown or death_unknown:
                    if birth_unknown: birthsymbol = '\u003f'   #  questionmark
                    if death_unknown: deathsymbol = '\u003f'
                elif birth_place == death_place:
                    birthsymbol = '\u2217/\u2020'
                    death_place = None    # no need to print the same name twice

                if node['label'] != '': node['label'] += line_delimiter
                if birth_place: node['label'] += '%s %s' % (birthsymbol, birth_place)
                if birth_place and death_place: node['label'] += ' / '
                if death_place: node['label'] += '%s %s' % (deathsymbol, death_place)
        else:
            if node['label'] != '': node['label'] += line_delimiter
            if birth_date: node['label'] += '%s %s ' % (birthsymbol, birth_date)
            if birth_place : node['label'] += birth_place
            if node['label'] != '': node['label'] += line_delimiter
            if death_date: node['label'] += '%s %s ' % (deathsymbol, death_date)
            if death_place : node['label'] += death_place

        # see if we have biological relationship (VerwandtschaftsGrad)
        if not pid in self.include["pidlist"] and \
           self.local_node and keys_exists(self.local_node, 'VG') and self.local_node['VG']['mode'] > 0 and \
           keys_exists(self.people[pid], 'VG', 'count'):
            if (self.local_node['VG']['mode'] == 1 and \
               len(self.people[pid]['VG']['generation'].items()) > 1) or \
               (self.local_node['VG']['mode'] == 2):
                gb = ''
                for k, v in sorted(self.people[pid]['VG']['generation'].items()):
                    gb += '%s<SUP>%s</SUP>' % (k, v)
                gsb = -math.log2(self.people[pid]['VG']['count'])

                line_deli = line_delimiter if self.local_node['VG']['line'] else ', '
                gb_str = '%s<I>g<SUB>b</SUB></I>: %s' % (line_delimiter, gb)
                gsb_str = "%s<I>g'<SUB>b</SUB></I>: %0.1f" % (line_deli, gsb)

                node['label'] += (gb_str + gsb_str)

        return None

    def include_gender(self, person, node):
        """"""
        def update(dict1, dict2, ident1, ident2, ident3, typ):
            extension = ''

            if keys_exists(dict1, ident2, ident3):
                if dict1[ident2][ident3] > 0.0 and typ == 'f':
                    extension += ' %s=%.2f' % (ident3, dict1[ident2][ident3])
                elif typ == 'd':
                    extension += ' %s=%d' % (ident3, dict1[ident2][ident3])
            else:
                if typ == 'f':
                    extension += ' %s=%.2f' % (ident3, dict2[ident1][ident3])
                elif typ == 'd':
                    extension += ' %s=%d' % (ident3, dict2[ident1][ident3])

            return extension

        node['extension'] = ''
        gender = person.get_gender()
        gender_str = 'unknown'
        if gender == Person.MALE: gender_str = 'male'
        elif gender == Person.FEMALE: gender_str = 'female'
        self.update_node(self.implex[gender_str], node)

        if gender == person.UNKNOWN:
            node['shape'] = "hexagon"
        else:
            node['extension'] = ''
            node['bordercolor'] = self.implex[gender_str]['bordercolor']
            node['extension'] += update(self.implex, self.node, 'person', gender_str, 'height', 'f')
            node['extension'] += update(self.implex, self.node, 'person', gender_str, 'width', 'f')
            node['extension'] += update(self.implex, self.node, 'person', gender_str, 'margin', 'f')
            node['extension'] += update(self.implex, self.node, 'person', gender_str, 'penwidth', 'd')

    def include_lineage(self, person, node, mode=False):
        """"""
        pid = person.gramps_id
        gender = person.get_gender()

        if gender == Person.MALE and self.local_path and 'male' in self.local_path:
            self.update_node(self.local_path['male'], node, mode)
        elif gender == Person.FEMALE and self.local_path and 'female' in self.local_path:
            self.update_node(self.local_path['female'], node, mode)
        elif gender == person.UNKNOWN:
            node['shape'] = "hexagon"

        # do we have target colours (even we have no path)
        if self.lineages and pid in self.lineages['target_set']:   # quick check
            for target in self.lineages['Targets']:
                if pid == target['ID']:
                    node['fillcolor'] = target['fillcolor']
                    node['fontcolor'] = target['fontcolor']
                    node['penwidth'] = target['penwidth']

        # do we have lineages source colours (even we have no path)
        if self.lineages and pid in self.lineages['source_set']:   # quick check
            for source in self.lineages['Sources']:
                if pid == source['ID']:
                    node['fillcolor'] = source['fillcolor']
                    node['fontcolor'] = source['fontcolor']
                    node['penwidth'] = source['penwidth']

        return True

    def write_individualnode(self, person):
        """"""
        def check_keys(*keys):
            if pid == 'I06788':
                a = 1
            result = False
            if not self.people[pid]['spouse']:
                if self.people[pid]['type'] == 'A':
                    result |= self.include['ancestor']['enable'] and keys_true(self.include, 'ancestor', keys) and \
                        not pid in self.color['ancestor']['uncolorlist']
                if self.people[pid]['type'] == 'P':
                    result |= self.include['proband']['enable'] and keys_true(self.include, 'proband', keys) and \
                        not pid in self.color['proband']['uncolorlist']
                if self.people[pid]['type'] == 'D':
                    result |= self.include['descendant']['enable'] and keys_true(self.include, 'descendant', keys) and \
                        not pid in self.color['descendant']['uncolorlist']
            else:
                if self.people[pid]['type'] == 'A':
                    result |= self.include['ancestorspouse']['enable'] and keys_true(self.include, 'ancestorspouse', keys) and \
                        not pid in self.color['ancestor']['uncolorlist']
                if self.people[pid]['type'] == 'P':
                    result |= self.include['probandspouse']['enable'] and keys_true(self.include, 'probandspouse', keys) and \
                        not pid in self.color['proband']['uncolorlist']
                if self.people[pid]['type'] == 'D':
                    result |= self.include['descendantspouse']['enable'] and keys_true(self.include, 'descendantspouse', keys) and \
                        not pid in self.color['descendant']['uncolorlist']
            return result

        pid = person.gramps_id
        surname = ordName(person).surname
        gender = person.get_gender()

        node = Node('I', pid, gender)

        if keys_exists(self.node, 'person'):
            if gender == Person.FEMALE and keys_exists(self.node['person'], 'female'):
                node.update(self.node['person']['female'])
            elif gender == Person.MALE and keys_exists(self.node['person'], 'male'):
                node.update(self.node['person']['male'])
            elif gender == Person.UNKNOWN and keys_exists(self.node['person'], 'default'):
                node.update(self.node['person']['default'])
            else:
                node.update(self.node['person'])
            node['htmloutput'] = self.diagram['ids'] != 0

        if keys_exists(self.diagram, 'number', 'markstart'):
            node['htmloutput'] |= self.diagram['number']['markstart'] != 'None'

        # see if we have Lineages
        if self.base["chart"].capitalize() == 'Lineage':
            self.include_lineage(person, node)

        # figure out what basic shape/style/color to use
        if self.base["chart"].capitalize() != 'Implex':
            gender_str = 'unknown'
            if gender == Person.MALE: gender_str = 'male'
            elif gender == Person.FEMALE: gender_str = 'female'
            if keys_exists(self.node, 'person', gender_str):
                node.update(self.node['person'][gender_str])
                node['fillcolor'] = self.node['person'][gender_str]['fillcolor']
                node['bordercolor'] = self.node['person'][gender_str]['bordercolor']

        # see if we have EndOfLine in Ancestors
        if self.people[pid]['type'] == 'A' and self.people[pid]['EoL'] and \
           keys_true(self.diagram, 'attribute', 'EoL', 'enable'):
            node['shape'] = self.diagram['attribute']['EoL']['shape']
            node['style'] = self.diagram['attribute']['EoL']['style']
            node['extension'] = self.diagram['attribute']['EoL']['extension']

        # see if we have descendant colours that match this person
        if self.color['descendant']:
            if keys_true(self.color, 'descendant', 'bordercolor'):
                node['bordercolor'] = self.color['descendant']['bordercolor']
            if keys_true(self.color, 'descendant', 'fillcolor'):
                node['fillcolor'] = self.color['descendant']['fillcolor']

        # see if we have Proband colours that match this person
        if pid in self.include['pidlist']:
            if 'proband' in self.color and \
              any(k in self.color['proband'] for k in ('male', 'female')):
                for proband in [self.color['proband']['male'], self.color['proband']['female']]:
                    if pid in proband['pid']:
                        if 'style' in proband: node['style'] = proband['style']
                        if 'bordercolor' in proband: node['bordercolor'] = proband['bordercolor']
                        node['fillcolor'] = proband['fillcolor']
                        node['fontcolor'] = proband['fontcolor']

        # see if we have Group names
        if self.nodegroup:
            for key, value in self.nodegroup.items():
                for value_id in value:
                    if value_id == pid:
                        node['extension'] += ' group="%s"' % key

        # see if we have Gradient colours that match this person
        if self.color['gradientcolor']:
            self.include_gradientcolor(person, node)

        # see if we have Degree colours that match this person
        if keys_true(self.color, 'degreecolor', 'enable'):
            self.include_degreecolor(person, node)

        # see if we have names with additional colors
        if surname in self.color['add-name']:
            node['fillcolor'] = self.color['add-name'][surname]['fillcolor']
            node['fontcolor'] = self.color['add-name'][surname]['fontcolor']

        # see if we have paternal / maternal colors
        if keys_exists(self.people[pid], 'base') and keys_exists(self.color, 'ancestor') and \
           self.people[pid]['base']['pid'] in self.color['ancestor']:
            node['base'] = True   # for Kekulé number

        if keys_exists(self.people[pid], 'XDNA') and self.people[pid]['XDNA']:
            self.include_xdnacolor(pid, node)

        # see if we have Pathes
        if keys_true(self.pathes, 'enable'):
            self.include_lineage(person, node)

        # see if we have Implex
        if self.base["chart"].capitalize() == 'Implex':
            if self.implex['pathes']['enable']:
                self.include_lineage(person, node, True)
            self.include_gender(person, node)

        # see if we have Level colours that match this generation
        if self.color['levelcolor'] and pid in self.generation:
            if check_keys('color'):
                self.include_levelcolor(self.generation[pid], node)
                if keys_true(self.include['descendantextra'], pid, "fillcolor"):
                    node['fillcolor'] = self.include['descendantextra'][pid]["fillcolor"]

        # see if we have persons with additional colors
        if pid == 'I00222':
            a = 1
        if pid in self.color['add-person']:
            node['fillcolor'] = self.color['add-person'][pid]['fillcolor']
            node['fontcolor'] = self.color['add-person'][pid]['fontcolor']

        # see if we have an image to use for this person
        self.diagram['images']['exist'] = False
        self.diagram['images']['enable'] = check_keys('images', 'enable')
        if self.diagram['images']['enable']:
            self.update_image_start(person, node)

        # see if we have a label dates we can use
        if self.diagram['ids'] or self.diagram['names'] or self.diagram['dates']['enable'] or self.diagram['places']['enable']:
            self.include_individuallabel(person, node)

        # see if we have a table that needs to be terminated
        self.update_image_stop(node)

        # self.update_node(self.node['default'], node)

        # color result
        if node['fontcolor']:
            node['extension'] += ' fontcolor="%s"' % node['fontcolor']
        if keys_exists(self.node, 'person', 'fontsize'):
            node['extension'] += ' fontsize="%d"' % int(self.node['person']['fontsize'])
        node['extension'] = node['extension'].replace('  ', ' ')   # Clean up
        # extension += ' xlabel="%s"' % name
        """
        # if we're filling the entire node:
        if self.colorize == 'filled':
            node['style'] += ",filled"
        elif self.colorize == 'outline':   # do not use hex_color if this is B&W outline
            node['border_color'], node['fillcolor'] = '', ''
        """
        # we're done -- add the node
        self.doc.add_node(pid, label=node['label'],
                          shape=node['shape'], color=node['bordercolor'], style=node['style'], fillcolor=node['fillcolor'],
                          htmloutput=node['htmloutput'], extension=node['extension'])
        return True

    # ------------------------------------------------------------------------------------------
    def include_family_VG(self, family, VGmode):   # VG: Verwandtschaftsgrad
        """"""
        gb_exist, gb_str, gsb_str = False, '', ''

        if self.local_node and keys_exists(self.local_node, 'VG') and self.local_node['VG']['mode'] == VGmode:
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            father_vg, mother_vg = None, None
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                if keys_exists(self.people[father.gramps_id], 'VG', 'count'):
                    father_ct = self.people[father.gramps_id]['VG']['count']
                    father_vg = self.people[father.gramps_id]['VG']['generation']
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                if keys_exists(self.people[mother.gramps_id], 'VG', 'count'):
                    mother_ct = self.people[mother.gramps_id]['VG']['count']
                    mother_vg = self.people[mother.gramps_id]['VG']['generation']

            if (father_vg and mother_vg):
                gb_exist, gb = True, ''

                vg_dict = defaultdict(list)
                for vg in (father_vg, mother_vg):
                    for key, value in vg.items():
                        vg_dict[key].append(value)
                for key, value in sorted(vg_dict.items()):
                    gb += '%s<SUP>%s</SUP>' % (key, sum(value))
                gsb = -math.log2(father_ct + mother_ct)

                gb_str = "<BR/><I>g<SUB>b</SUB></I>: %s" % gb
                gsb_str = "<I>g'<SUB>b</SUB></I>: %0.1f" % gsb

        return gb_exist, gb_str, gsb_str

    def include_familylabel(self, family, node):
        """"""
        def get_date_place(event):
            date, place = '', ''
            # get the date
            if self.diagram['dates']['enable']:
                date = event.get_date_object()
                if self.diagram['dates']['onlyyears'] and date.get_year_valid():   # localized year
                    date = self._get_date(Date(date.get_year()))
                else:
                    date = self._get_date(date)

            # get the event location
            if self.diagram['places']['enable']:
                place_type, place = get_event_place(self.database, event, True)
                if not self.diagram['places']['extended'] and \
                   place_type in ['Dom', 'Kapelle', 'Kirche', 'Kloster']:
                    place = place.split(', ')[1]
                if not event.get_type() == EventType.DIVORCE and \
                   place_type not in ['Dom', 'Kapelle', 'Kirche', 'Kloster']:
                    # a = event.get_type().string
                    if place and not place.endswith(' '): place += ' '
                    if event.get_type() == EventType.MARRIAGE:
                        place += '(Civil)'
                    if (event.get_type().value == EventType.CUSTOM and event.get_type().string == 'Trauung'):
                        place += '(Kirche)'

            return date, place

        family_id = family.get_gramps_id()
        if family_id == 'F0708':
            a = 1

        # figure out a wedding date or placename we can use
        marriage_date, marriage_place, wedding_date, wedding_place, \
            divorce_date, divorce_place = None, None, None, None, None, None
        if self.diagram['dates']['enable'] or self.diagram['places']['enable']:
          # (self.diagram['places']['images'] and self.diagram['images']['exist'])
            for event_ref in family.get_event_ref_list():
                event = self.database.get_event_from_handle(event_ref.ref)
                if not (event_ref.get_role() == EventRoleType.FAMILY or
                        event_ref.get_role() == EventRoleType.PRIMARY): continue

                if (node['type'] == 'A' and keys_true(self.include, 'ancestorfamily', 'civil')) or \
                   (node['type'] == 'P' and keys_true(self.include, 'probandfamily', 'civil')) or \
                   (node['type'] == 'D' and keys_true(self.include, 'descendantfamily', 'civil')):
                    if event.get_type() == EventType.MARRIAGE:
                        marriage_date, marriage_place = get_date_place(event)
                    if event.get_type() == EventType.DIVORCE:
                        divorce_date, divorce_place = get_date_place(event)

                if (node['type'] == 'A' and keys_true(self.include, 'ancestorfamily', 'church')) or \
                   (node['type'] == 'P' and keys_true(self.include, 'probandfamily', 'church')) or \
                   (node['type'] == 'D' and keys_true(self.include, 'descendantfamily', 'church')):
                    evalue = event.get_type().value
                    estring = event.get_type().string
                    if (event.get_type().value == EventType.CUSTOM and event.get_type().string == 'Trauung'):
                        wedding_date, wedding_place = get_date_place(event)

                if keys_true(self.include, 'descendantfamilyextra') and \
                   family_id in self.include['descendantfamilyextra']:
                    value = self.include['descendantfamilyextra'][family_id]
                    if 'civil' in value and value['civil'] and \
                       event.get_type() == EventType.MARRIAGE:
                        marriage_date, marriage_place = get_date_place(event)
                    if 'church' in value and value['church'] and \
                       (event.get_type() == EventType.CUSTOM and event.get_type().string == 'Trauung'):
                        wedding_date, wedding_place = get_date_place(event)

        # figure out the number of children (if any)
        children_str = None
        if (self.include['ancestorfamily']['childscount'] and self.generation[family_id] < 0) or \
           (self.include['probandfamily']['childscount']) or \
           (self.include['descendantfamily']['childscount'] and self.generation[family_id] > 0):
            child_count = len(family.get_child_ref_list())
            if child_count >= 1:
                children_str = self.ngettext("{number_of} child", "{number_of} children", \
                                             child_count).format(number_of=child_count)

        # see if we have biological relationship
        gb_exist, gb_str, gsb_str = self.include_family_VG(family, 2)
        node['htmloutput'] |= gb_exist
        line_delimiter = '<BR/>' if node['htmloutput'] else '\\n'

        """
        if self.diagram['ids'] == 1:
            node['label'] += "<SUB>[%s]</SUB>" % family_id
        elif self.diagram['ids'] == 2: # own line
        """
        if self.diagram['ids']['style'] == 2:   # IDs in own line
            node['label'] += '%s[%s]%s' % \
                (self.diagram['ids']['markstart'], family_id, self.diagram['ids']['markstop'])

        if marriage_date or marriage_place:
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += '\u26AD'
            if marriage_date: node['label'] += ' %s' % marriage_date
            if keys_true(self.include, 'descendantfamily', 'line'):
                node['label'] += line_delimiter \
                    if not (marriage_date and wedding_date) else ' '
            if marriage_place: node['label'] += ' %s' % marriage_place

        if wedding_date or wedding_place:
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += '\u26AD'
            if wedding_date: node['label'] += ' %s' % wedding_date
            if keys_true(self.include, 'descendantfamily', 'line'):
                node['label'] += line_delimiter \
                    if not (marriage_date and wedding_date) else ' '
            if wedding_place: node['label'] += ' %s' % wedding_place

        if divorce_date or divorce_place:
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += '\u26AE'
            if divorce_date: node['label'] += ' %s' % divorce_date
            if divorce_place: node['label'] += ' %s' % divorce_place

        # see if we have children
        if children_str:
            if node['label'] != '': node['label'] += line_delimiter
            node['label'] += '%s' % children_str

        # see if we have biological relationship
        if gb_exist:
            node['label'] += '%s, %s' % (gb_str, gsb_str)

    def write_familynode(self, family, ftype):
        """"""
        family_id = family.get_gramps_id()
        family_type = family.type.string
        family_value = family.type.value

        node = Node('F', family_id)
        self.update_node(self.node['family'], node)
        # node.update(self.node['family'])
        node['type'] = ftype
        node['htmloutput'] = self.diagram['ids'] != 0

        # see if we have an image to use for this family
        # self.update_image_start(family, node)

        # see if we have dates we can use
        if self.diagram['ids'] or self.diagram['names'] or \
           self.diagram['dates']['enable'] or self.diagram['places']['enable']:
            self.include_familylabel(family, node)

        # see if we have a table that needs to be terminated
        # self.update_image_stop(node)

        if family_value == 1:   # Unverheiratet!
            node['style'] += ',dotted'

        # see if we have names with additional colors
        if family_id in self.color['add-family']:
            node['fillcolor'] = self.color['add-family'][family_id]['fillcolor']
            node['fontcolor'] = self.color['add-family'][family_id]['fontcolor']

        if node['style'] == 'invisible':
            node['bordercolor'], node['fillcolor'] = '#000000', '#000000'
            node['extension'] += ', height=0, width=0, margin=0'
        else:
            node['extension'] += "margin=0"

        # extra rules for 'Implex'
        if self.base["chart"].capitalize() == 'Implex' and self.base["style"] == 'extended':
            if self.diagram['ids'] > 0:
                node['extension'] += ' xlabel="[%s]"' % family_id

        # self.update_node(self.node['default'], node)

        # color result
        if node['fontcolor']:
            node['extension'] += ' fontcolor="%s"' % node['fontcolor']
        if keys_exists(self.node, 'family', 'fontsize'):
            node['extension'] += ' fontsize="%d"' % int(self.node['family']['fontsize'])
        node['extension'] = node['extension'].replace('  ', ' ')   # Clean up
        """
        # if we're filling the entire node:
        if self.colorize == 'filled':
            node['style'] += ",filled"
        elif self.colorize == 'outline':   # do not use hex_color if this is B&W outline
            node['bordercolor'], node['fillcolor'] = '', ''
        """
        # we're done -- add the node
        self.doc.add_node(family_id, label=node['label'],
                          shape=node['shape'], color=node['bordercolor'], style=node['style'], fillcolor=node['fillcolor'],
                          htmloutput=node['htmloutput'], extension=node['extension'])

    # ------------------------------------------------------------------------------------------
    def compile_pathlink(self, key, data):
        """"""
        if key in self.lineages['Edges']:
            data['source'] = 'path'   # Debug

            path_name = self.lineages['Edges'][key][0]
            data['style'][path_name] = self.lineages['Edges'][key][1]
            data['color'][path_name] = self.lineages['Edges'][key][2]
            data['penwidth'][path_name] = self.lineages['Edges'][key][3]

    def compile_cyclelink(self, indkey, famkey2, data):
        """"""
        for key, value in self.implex['circuits'].items():
            key1 = '%s-%s' % (indkey, famkey2)
            key2 = '%s-%s' % (famkey2, indkey)
            if key1 in value or key2 in value:
                cyc_key = 'cycle%02d' % key
                if keys_exists(self.implex['cycles'], cyc_key):
                    data['source'] = 'cycle'   # Debug

                    col_key = self.implex['cycles'][cyc_key]['color']
                    col_rgb = self.color['base'].IttenC5[col_key]['RGB']
                    data['color'][cyc_key] = self.color['base'].RGBtoHEX(col_rgb)
                    data['style'][cyc_key] = self.implex['cycles'][cyc_key]['style']
                    data['penwidth'][cyc_key] = self.implex['cycles'][cyc_key]['penwidth']
                    a = 1

        return True

    def write_individuallink(self, family, person, fontcolor=''):
        """ write the link between person and families """
        # stype = ['ortho', 'polyline', 'spline', 'line']
        # sbool = any(x in self.dot['spline'] for x in stype)

        person_rn = person.get_primary_name().get_regular_name()
        pid = person.get_gramps_id()
        # if sbool: person_str += ':s'

        family_id = family.get_gramps_id()
        # if sbool: family_str += ':n'

        extension, style = '', 'filled'
        PFkey = '%s-%s' % (pid, family.gramps_id)
        FPkey = '%s-%s' % (family.gramps_id, pid)

        if family_id == 'F0084':
            a = 1

        if self.local_path:
            key = FPkey if FPkey in self.lineages['Edges'] else PFkey
            if key in self.lineages['Edges']:
                style = self.lineages['Edges'][key][1]
                extension += 'color="%s" penwidth=%.1f' % \
                                (self.lineages['Edges'][key][2], \
                                 self.lineages['Edges'][key][3])

                if keys_exists(self.local_path, 'edge', 'HenryNo') and self.local_path['edge']['HenryNo']:
                    distance = 1
                    label = ''
                    henryno_list = sorted(self.people[pid]['HenryNo'], key=len)
                    for l, lbl in enumerate(henryno_list):
                        if lbl == '1': continue
                        label += ' %s' % lbl

                    labelspace = ''
                    if keys_exists(self.local_path, 'additional', 'labelspace'):
                        edge = '%s-%s' % (pid, family_id)
                        if edge in self.local_path['additional']['labelspace']:
                            labelspace = ' '*(self.local_path['additional']['labelspace'][edge])

                    extension += ' taillabel="\n%s%s" labelfontcolor="%s" ' % \
                       (label, labelspace, fontcolor)   # labeldistance="%.1f" distance

        # Check if minimum length required (vertical)
        if self.noteshift:
            for key, value in self.noteshift.items():
                if key == PFkey:
                    extension += ' minlen=%d' % value['shift']

        name = 'Father' if person.gender == 1 else 'Mother'
        comment = self._("%s: %s") % (name, person_rn)

        # we're done -- add the link
        self.doc.add_link(id1=pid, id2=family_id, style=style,
                        head=self.edge['arrowheadstyle'], tail=self.edge['arrowtailstyle'],
                            extension=extension, comment=comment)

    def write_parentimplexlink(self, family, father, mother):
        """"""
        def compile_node(self, person, fontcolor):
            """"""
            data = {
                'source': 'board',   # Debug

                'pid': person.get_gramps_id(),
                'name': person.get_primary_name().get_regular_name(),
                'gender': person.gender,
                'length': 0, 'minlen': self.edge['minlen'],
                'label': '', 'xlabel': '', 'edgelabel': '',
                'comment': self._("Person: %s") % person.get_primary_name().get_regular_name(),

                'style': { 'base': 'solid'},
                'color': { 'base': 'black'},
                'head': self.edge['arrowheadstyle'], 'tail': self.edge['arrowtailstyle'],
                'penwidth': { 'base': 1 },
            }

            if data['pid'] in self.people and self.people[data['pid']]['HenryNo']:
                distance = 0
                label = ''   # '\n' if person.gender == 1 else ''
                # label += '\n'*len(self.people[data['pid']]['HenryNo'])
                henryno_list = sorted(self.people[data['pid']]['HenryNo'], key=len)
                for l, lbl in enumerate(henryno_list):
                    data['length'] = max(len(lbl), data['length'])
                    distance = max(_LABELDIST[len(lbl)], distance)   #  length of Henry number
                    label += ' %s\n' % lbl
                    a = 1

                if person.gender == 1: label += '\n'
                label = ''
                data['label'] = 'label="%s"' % label
                data['minlen'] = 1 # (-(-len(self.people[data['pid']]['HenryNo']) // 2))   # Aufrunden nach Teilung durch 2
                data['edgelabel'] = 'taillabel="%s" labelfontcolor="%s"' % \
                    (label, fontcolor)   # labelangle=90 labeldistance="%.1f" distance,
                if person.gender == Person.MALE: data['edgelabel'] += ' labelangle=0 ' # labeldistance=-%.1f % 1
                #    (distance)   # labelangle=90 ="" ,

            return data

        def write_coreedge(self, data):
            """"""
            for i, key in enumerate(data['style']):
                if (len(data['style']) > 1) and key == 'base': continue

                extension = 'color="%s" penwidth=%.1f' % (data['color'][key], data['penwidth'][key])
                comment = '%d. Edge %s' % (i, data['comment'])

                self.doc.add_link(id1=data['pid'], id2=family_id, style=data['style'][key],
                                  head=data['head'], tail=data['tail'], extension=extension, comment=comment)

        def write_extstartedge(self, data, end=True):
            """"""
            self.doc.start_subgraph(data['pid'])
            extension = 'color="grey" height=0 width=0 margin=0'   # invis. Node
            self.doc.add_node("inv"+data['pid'], shape="point", extension=extension)

            for i, key in enumerate(data['style']):
                if (len(data['style']) > 1) and key == 'base': continue

                extension = 'color="%s" penwidth=%d ' % (data['color'][key], data['penwidth'][key])
                comment = '%d. invis. Edge %s' % (i, data['comment'])
                self.doc.add_link(id1=data['pid'], id2="inv"+data['pid'],   # +":s", +":n"
                                    style=data['style'][key], head="none", tail="none",
                                    extension=extension, comment=comment)
            if end: self.doc.end_subgraph()

        def write_extendedge(self, data, rotate=False):
            """"""
            for i, key in enumerate(data['style']):
                if (len(data['style']) > 1) and key == 'base': continue

                extension = 'color="%s" penwidth=%.1f' % (data['color'][key], data['penwidth'][key])
                if i == len(data['style']) -1: extension += ' %s' % data['edgelabel']
                if i == len(data['style']) -1: extension += ' minlen="%s"' % data['minlen']
                comment = '%d. Edge %s' % (i, data['comment'])

                if rotate:
                    if data['gender'] == 0:   # Female
                        self.doc.add_link(id1="inv"+data['pid'], id2=family_id, style=data['style'][key],
                                          head="none", tail="none", extension=extension, comment=comment)
                    if data['gender'] == 1:   # Male
                        self.doc.add_link(id1=family_id, id2="inv"+data['pid'], style=data['style'][key],
                                          head="none", tail="none", extension=extension, comment=comment)
                else:
                    if data['gender'] == 0:   # Female
                        self.doc.add_link(id1=family_id, id2="inv"+data['pid'], style=data['style'][key],
                                          head="none", tail="none", extension=extension, comment=comment)
                    if data['gender'] == 1:   # Male
                        self.doc.add_link(id1="inv"+data['pid'], id2=family_id, style=data['style'][key],
                                          head="none", tail="none", extension=extension, comment=comment)

        if family:
            family_id = family.get_gramps_id()
            if keys_exists(self.implex, 'cluster', 'FID') and \
               family_id in self.implex['cluster']['FID']:   # debug!
                line = '  style=dashed;\n' if self.implex['cluster']['debug'] else ''
                if line: self.doc.write(line)

        fdata, mdata = None, None
        rotate = self.noderotate and family_id in self.noderotate
        # see if we have a father to link to this family
        if father and father.gramps_id in self.implex['Ind']:
            fdata = compile_node(self, father, self.implex['male']['fontcolor'])

            if self.implex['pathes']['enable']:
                FFkey = '%s-%s' % (father.gramps_id, family.gramps_id)
                self.compile_pathlink(FFkey, fdata)
            if self.implex['cycles']['enable']:
                self.compile_cyclelink(father.gramps_id, family.gramps_id, fdata)

        # see if we have a mother to link to this family
        if mother and mother.gramps_id in self.implex['Ind']:
            mdata = compile_node(self, mother, self.implex['female']['fontcolor'])

            if self.implex['pathes']['enable']:
                MFkey = '%s-%s' % (mother.gramps_id, family.gramps_id)
                self.compile_pathlink(MFkey, mdata)
            if self.implex['cycles']['enable']:
                self.compile_cyclelink(mother.gramps_id, family.gramps_id, mdata)

        if self.base["style"] == 'core':
            if self.include['relativspouse']:
                # force the node in a line from left to right
                if (father and father.gramps_id in self.people) and \
                   (mother and mother.gramps_id in self.people):   # maybee None
                    if rotate:
                        self.doc.write('  { rank = same; %s -> %s [style=invis] }\n' % \
                                   (mother.get_gramps_id(), father.get_gramps_id()) )
                    else:
                        self.doc.write('  { rank = same; %s -> %s [style=invis] }\n' % \
                                   (father.get_gramps_id(), mother.get_gramps_id()) )

            if (mother and mdata): write_coreedge(self, mdata)
            if (father and fdata): write_coreedge(self, fdata)

        if self.base["style"] == 'extended':
            if father and father.gramps_id in self.implex['Ind']:
                write_extstartedge(self, fdata)

            # do we need additional space?
            ext_spacer = "margin=0 penwidth=0 "
            ext_spacer += 'height=%.2f' % self.node['person']['spacer']['height'] \
                if 'height' in self.node['person']['spacer'] and self.node['person']['spacer']['height'] else \
                'height=%.2f' % self.node['person']['height']
            ext_spacer += ' width=%.2f' % self.node['person']['spacer']['width'] \
                if 'width' in self.node['person']['spacer'] and self.node['person']['spacer']['width'] else \
                ' width=%.2f' % self.node['person']['width']

            # see if we have a mother to link to this family
            fspacer = False
            if mother and mother.gramps_id in self.implex['Ind']:
                write_extstartedge(self, mdata, False)

                # do we need additional space?
                if keys_exists(self.implex, 'cluster', 'FID') and \
                   family_id in self.implex['cluster']['FID']:
                    fspacer = True

                    self.doc.add_node('spc'+mdata['pid'], shape="circle", style="invis", extension=ext_spacer)   # invis. Node
                    self.doc.add_link(id1=mdata['pid']+':e', id2='spc'+mdata['pid']+":w", style="invis",
                                      head="none", tail="none", comment="invis. circle")
                    if mdata['length'] > 10:
                        self.doc.add_node('spc'+fdata['pid'], shape="circle", style="invis", extension=ext_spacer)   # invis. Node

                self.doc.end_subgraph()
                if fspacer:
                    rank_str = '  { rank = same; %s; %s } // Spacer\n\n' % (mdata['pid'], 'spc'+mdata['pid']) \
                        if mdata['length'] < 11 else \
                        '  { rank = same; %s; %s; %s; %s } // Spacer\n\n' % \
                       ('spc'+fdata['pid'], fdata['pid'], mdata['pid'], 'spc'+mdata['pid'])
                    self.doc.write(rank_str)

            # we're done -- add the link
            if family:
                # Node with Link from Family-Node to invisible Node (EdgeSpacer!)
                if self.implex['edge']['spacer']:
                    self.doc.start_subgraph("inv"+family_id)
                    label, style = "", ""
                    if not self.implex['family']['debug'] % 2:   # number is odd
                        label, style = family_id, "invis"
                    self.doc.add_node("inv"+family_id, label=label, shape="box", style=style, extension=ext_spacer)   # (invis.) Node
                    if self.implex['family']['debug'] > 1:   # number contains '2'
                        style = "invis"
                    self.doc.add_link("inv"+family_id+':s', id2=family_id+":n", style=style,
                                       head="none", tail="none", comment="invis. box")
                    self.doc.end_subgraph()

                if self.implex['xlabel']['enable'] and \
                   keys_exists(self.implex, 'xlabel', 'sticker'):
                    for stick in self.implex['xlabel']['sticker'].items():
                        if stick[0].startswith('cycle') or stick[0].startswith('mark'):
                            label = stick[1]['label']
                        else: continue

                        if family_id == stick[1]['base_id']:
                            if self.usesubgraphs: self.doc.start_subgraph(stick[0])
                            xlbl = 'xLbl_%s' % label
                            style = self.implex['xlabel']['edge']['style']
                            penwidth = stick[1]['penwidth'] if keys_exists(stick[1], 'penwidth') else 1
                            color = stick[1]['color'] if keys_exists(stick[1], 'color') else self.implex['xlabel']['edge']['color']

                            if stick[0].startswith('cycle'):
                                edge = self.implex['cycles'][stick[0]]

                                if keys_exists(stick[1], 'color'): color_code = stick[1]['color']
                                else: color_code = edge['color']
                                col_rgb = self.color['base'].IttenC5[color_code]['RGB']
                                color = self.color['base'].RGBtoHEX(col_rgb)

                                if not keys_exists(stick[1], 'penwidth'): penwidth = edge['penwidth']
                                style = edge['style']

                            extension = 'color="%s" penwidth=%.1d' % (color, penwidth)
                            comment = 'XLabel: Node %s' % label
                            self.doc.add_link(id1=xlbl, id2=stick[1]['base_id'], style=style,
                                              extension=extension, comment=comment)
                            if self.usesubgraphs: self.doc.end_subgraph()
                            break

                rank_str = ''
                if (father and fdata) and (mother and mdata):
                    rank_str = '  { rank = same; %s; %s; %s } // Fam: %s -- %s\n' % \
                        ("inv"+fdata['pid'], family_id, "inv"+mdata['pid'], fdata['name'], mdata['name'])
                elif (father and fdata) and not (mother and mdata):
                    rank_str = '  { rank = same; %s; %s } // Fam: %s\n' % \
                        ("inv"+fdata['pid'], family_id, fdata['name'])
                elif not (father and fdata) and (mother and mdata):
                    rank_str = '  { rank = same; %s; %s } // Fam: %s\n' % \
                        (family_id, "inv"+mdata['pid'], mdata['name'])
                if rank_str:
                    self.doc.write(rank_str)

            if (father and fdata):
                write_extendedge(self, fdata, rotate)
            if (mother and mdata):
                write_extendedge(self, mdata, rotate)

        return None

    def write_parentlink(self, family, direction='FM'):
        """ write the link between parents and families """

        # get the parents for this family
        father_handle = family.get_father_handle()
        father = self.database.get_person_from_handle(father_handle) if father_handle else None
        mother_handle = family.get_mother_handle()
        mother = self.database.get_person_from_handle(mother_handle) if mother_handle else None

        if self.base["chart"].capitalize() == 'Board' or \
           self.base["chart"].capitalize() == 'Lineage':
            if direction == 'FM':   # Father -- Mother
                if self.include['relativspouse']:
                    # force the node in a line from left to right
                    if (father and father.gramps_id in self.people) and \
                       (mother and mother.gramps_id in self.people):   # maybee None
                        self.doc.write('  { rank = same; %s -> %s [style=invis] }\n' % \
                                       (father.get_gramps_id(), mother.get_gramps_id()) )

                # see if we have a father to link to this family
                if father and father.gramps_id in self.people:
                    fontcolor = self.local_path['edge']['male']['fontcolor'] \
                        if self.local_path and keys_exists(self.local_path, 'edge', 'male', 'fontcolor') else ''
                    self.write_individuallink(family, father, fontcolor)
                # see if we have a mother to link to this family
                if mother and mother.gramps_id in self.people:
                    fontcolor = self.local_path['edge']['female']['fontcolor'] \
                        if self.local_path and keys_exists(self.local_path, 'edge', 'female', 'fontcolor') else ''
                    self.write_individuallink(family, mother, fontcolor)

            if direction == 'MF':   # Mother -- Father
                if self.include['relativspouse']:
                    # force the node in a line from left to right
                    if father and mother:   # maybee None
                        self.doc.write('  { rank = same; %s -> %s [style=invis] }\n' % \
                                       (mother.get_gramps_id(), father.get_gramps_id()) )

                # see if we have a mother to link to this family
                if mother and mother.gramps_id in self.people:
                    fontcolor = self.local_path['edge']['male']['fontcolor'] \
                        if self.local_path and keys_exists(self.local_path, 'edge', 'male', 'fontcolor') else ''
                    self.write_individuallink(family, mother, fontcolor)
                # see if we have a father to link to this family
                if father and father.gramps_id in self.people:
                    fontcolor = self.local_path['edge']['female']['fontcolor'] \
                        if self.local_path and keys_exists(self.local_path, 'edge', 'female', 'fontcolor') else ''
                    self.write_individuallink(family, father, fontcolor)

        if self.base["chart"].capitalize() == 'Implex':
            self.write_parentimplexlink(family, father, mother)

    def write_childrenlink(self, family):
        """ write the link between families and children """

        def compile_node(self, person, style, color, width):
            """"""
            data = {
                'source': 'board',   # Debug
                'pid': person.get_gramps_id(),
                'name': person.get_primary_name().get_regular_name(),
                'minlen': self.edge['minlen'],
                'comment': '',

                'style': { 'base': 'solid'},
                'color': { 'base': 'black'},
                'penwidth': { 'base': 1 }
            }
            data['comment'] = self._("child: %s") % data['name']

            return data

        def write_endedge(data):
            """"""
            for i, key in enumerate(data['style']):
                if key == 'base' and  (len(data['style']) > 1) and data['style']['base'] == 'solid':
                    continue

                # print('ID: %s' % data['pid'])
                extension = 'color="%s" penwidth=%.1f' % (data['color'][key], data['penwidth'][key])
                # if i == len(data['style']) -1: extension += ' minlen="%s"' % data['minlen']
                comment = '%d. %s' % (i, data['comment'])

                self.doc.add_link(id1=family_id, id2=child_id, style=data['style'][key],
                                  head=self.edge['arrowheadstyle'], tail=self.edge['arrowtailstyle'],
                                  extension=extension, comment=comment)

        # stype = ['ortho', 'polyline', 'spline']
        # sbool = any(x in self.dot['spline'] for x in stype)

        family_id = family.get_gramps_id()
        # if sbool: family_str += ':s'

        # link the children to the family
        for childref in family.get_child_ref_list():
            if not childref.ref:
                continue

            child = self.database.get_person_from_handle(childref.ref)
            if child and child.gramps_id in self.people:
                child_id = '%s' % child.get_gramps_id()
                # if sbool: child_str += ':n'

                if child_id == 'I17286':
                    a = 1

                cdata = compile_node(self, child, 'filled', 'black', 1)

                # Family -- Child key
                FCkey = '%s-%s' % (family.gramps_id, child.get_gramps_id())
                CFkey = '%s-%s' % (child.get_gramps_id(), family.gramps_id)
                # see if we have Lineages
                if self.local_path and keys_true(self.local_path, 'enable'):
                    key = CFkey if CFkey in self.lineages['Edges'] else FCkey
                    self.compile_pathlink(key, cdata)

                    # Father- or Mother-Relation not biological (parents)
                    if childref.frel.value != 1 or childref.mrel.value != 1:
                        cdata['style']['base'] = 'dashed'

                # Check if minimum length required (vertical)
                if self.noteshift:
                    for key, value in self.noteshift.items():
                        if key == FCkey:
                            cdata['minlen'] = value['shift']

                if self.base["chart"].capitalize() == 'Board':
                    if self.pathes['enable']:
                        self.compile_pathlink(FCkey, cdata)
                if self.base["chart"].capitalize() == 'Lineage':
                    if child.gramps_id not in self.lineages['Ind'].keys():
                        continue
                if self.base["chart"].capitalize() == 'Implex':
                    if childref.ref not in self.implex['Ind'].values():
                        continue

                    if self.implex['pathes']['enable']:
                        self.compile_pathlink(FCkey, cdata)
                    if self.implex['cycles']['enable']:
                        self.compile_cyclelink(child.gramps_id, family.gramps_id, cdata)

                # we're done -- add the link
                write_endedge(cdata)

    # -------------------------------------------------------------------------------------------------------------------------
    def write_persons(self):
        """ write the Persons """
        # --->
        local_people = {}
        # <---

        self.doc.add_comment('')

        self.penwidth = self.node['person']['penwidth'] if 'penwidth' in self.node['person'] else 2

        # If attempt to include images, use the HTML style of .gv file.
        # use_html_output = self.diagram['images']['enable']

        # check if we have Board
        if self.base["chart"].capitalize() == 'Board':
            local_people = self.people
        # check if we have Lineages
        if self.base["chart"].capitalize() == 'Lineage':
            local_people = self.lineages['Ind']
        # check if we have Implex
        if self.base["chart"].capitalize() == 'Implex':
            if keys_exists(self.implex, 'Ind'):
                local_people = self.implex['Ind']
                if keys_true(self.implex, 'xlabel', 'enable'):
                    self.write_node_xlabel(self.implex['xlabel'])

            # Add additional people
            for key, value in self.include['descendantextra'].items():
                if key not in local_people and key in self.people:
                    local_people[key] = self.people[key]['handle']

        # loop through all the people we need to output
        for pid in local_people: # sorted()
            # ptype = local_people[pid]['type']
            person = self.database.get_person_from_gramps_id(pid)
            self.write_individualnode(person)

        # check if we have ranks
        if local_people and self.noderank:   # local_people maybee NIL
            self.doc.add_comment('')
            for key, value in self.noderank.items():
                value_str = '{ rank = same; '
                for v in value: value_str += '%s; ' % v
                self.doc.write(' %s} // Level: %s\n' % (value_str, key))

    def write_families(self):
        """ write the families """
        # --->
        local_families = {}
        # <---

        self.doc.add_comment('')
        self.ngettext = self._locale.translation.ngettext # to see "nearby" comments

        # check if we have Board
        if self.base["chart"].capitalize() == 'Board':
            local_families = self.families
        # check if we have Lineages
        if self.base["chart"].capitalize() == 'Lineage':
            local_families = self.lineages['Fam']
        # check if we have Implex
        if self.base["chart"].capitalize() == 'Implex':
            if keys_exists(self.implex, 'Fam'):
                local_families = self.implex['Fam']

        # loop through all the families we need to output
        for family_id in sorted(local_families):
            ftype = local_families[family_id]['type']
            family = self.database.get_family_from_gramps_id(family_id)
            self.write_familynode(family, ftype)

        # check if we have ranks
        if keys_exists(self.node, 'family', 'rank') and self.node['family']['rank']:
            self.doc.add_comment('')
            for key, value in sorted(self.node['rank'].items()):
                if isinstance(key, int): continue

                value_str = '{ rank = same; ' # !key
                for v in value: value_str += '"%s"; ' % v
                self.doc.write('  %s} // Gen: %s\n' % (value_str, key))

    def write_links(self):
        """ write the links between individuals and families """
        # --->
        local_families = {}
        # <---

        # check if we have Cluster
        if self.nodecluster:
            self.doc.add_comment('')

            node_cluster = []
            for key, value in self.nodecluster.items():
                if key not in node_cluster:

                    self.doc.start_subgraph(key)
                    for nr, value_id in enumerate(value):
                        family = self.database.get_family_from_gramps_id(value_id)
                        if family:
                            if nr % 2 == 0: self.write_parentlink(family, 'MF')
                            else: self.write_parentlink(family, 'FM')

                        if value_id in self.families:
                            del self.families[value_id]
                    self.doc.end_subgraph()

                    for nr, value_id in enumerate(value):
                        family = self.database.get_family_from_gramps_id(value_id)
                        if family: self.write_childrenlink(family)

                    node_cluster.append(key)

        # check if we have Groups
        if self.nodegroup:
            self.doc.add_comment('')

            node_groups = []
            for key, value in self.nodegroup.items():
                if key not in node_groups:
                    if self.usesubgraphs: self.doc.start_subgraph(key)
                    else: self.doc.write('edge[style=invis];\n')

                    for value_id in value[1:]:
                        self.doc.write('  "%s" -> "%s" [ style="invis" ];\n' % (value[0], value_id))

                    if self.usesubgraphs: self.doc.end_subgraph()

                    node_groups.append(key)

        # check if we have Board
        if self.base["chart"].capitalize() == 'Board':
            local_families = self.families
        # check if we have Lineages
        if self.base["chart"].capitalize() == 'Lineage':
            local_families = self.lineages['Fam']
        # check if we have Implex
        if self.base["chart"].capitalize() == 'Implex':
            if keys_exists(self.implex, 'Fam'):
                local_families = self.implex['Fam']

        # link the parents and children to the families
        for family_id in local_families:
            family = self.database.get_family_from_gramps_id(family_id)
            if family_id == 'Fxxxx':
                a = 1

            self.doc.add_comment('')
            if self.usesubgraphs: self.doc.start_subgraph(family_id)

            if self.noderotate and family_id in self.noderotate:
                self.write_parentlink(family, 'MF')
            else:
                self.write_parentlink(family, 'FM')
            if self.usesubgraphs: self.doc.end_subgraph()

            self.write_childrenlink(family)

    # -------------------------------------------------------------------------------------------------------------------------
    def apply_node_extra(self, extra):
        """"""
        handle_dict = {}
        for key in extra:
            person = self.database.get_person_from_gramps_id(key)
            handle_dict[key] = person.handle

        return handle_dict

    def write_node_extra(self, extra):
        """"""
        for key, value in extra.items():
            person = self.database.get_person_from_gramps_id(key)
            pid = person.gramps_id
            gender = person.get_gender()

            node = Node('I', pid, gender)
            node.update(value)
            node['htmloutput'] = self.diagram['ids'] != 0
            """
            self.doc.add_node(node['id'], label=node['label'],
                              shape=node['shape'], color=node['bordercolor'], style=node['style'], fillcolor=node['fillcolor'],
                              htmloutput=node['htmloutput'], extension=node['extension'])
            """

    def write_node_xlabel(self, xlabel):
        """"""
        for stick in xlabel['sticker'].items():
            if stick[0].startswith('cycle') or stick[0].startswith('mark'):
                ident = stick[1]['label']
            else: continue

            use_html_output = False
            label = stick[1]['label']
            if '_' in stick[1]['label']:
                use_html_output = True
                items = stick[1]['label'].split('_')
                label = '%s<SUB>%s</SUB>' % (items[0], items[1])

            node = {'id': 'xLbl_%s' % ident,
                    'htmloutput': use_html_output,
                    'shape': '', 'style': xlabel['node']['style'],
                    'label': label,
                    'extension': 'fontsize="%s" fontcolor="%s" height="%s" width="%s" margin="%s"' % \
                        (xlabel['node']['fontsize'], xlabel['node']['fontcolor'],
                         xlabel['node']['height'], xlabel['node']['width'], xlabel['node']['margin']),
                    'bordercolor': xlabel['node']['bordercolor'],
                    'fillcolor': '', 'fontcolor': ''
                    }
            if stick[0].startswith('mark'):
                node['extension'] += ' fontname="Liberation Serif Bold"'
            if stick[0].startswith('cycle') and \
               keys_exists(self.local_node, 'VG') and self.local_node['VG']['mode'] > 0:
                family = self.database.get_family_from_gramps_id(stick[1]['base_id'])
                if family:
                    if stick[1]['base_id'] == "F0168":
                        a = 1
                    gb_exist, gb_str, gsb_str = self.include_family_VG(family, 1)
                    if gb_exist:
                        node['htmloutput'] = True
                        node['label'] += '<FONT POINT-SIZE="%s" FACE="%s"><BR/>%s<BR/>%s</FONT>' % \
                            (int(self.node['family']['fontsize']), self.dot['font']['family'], gb_str, gsb_str)
                        node['shape'] = 'ellipse'

            self.update_node(xlabel['node'], node)

            # we're done -- add the node
            self.doc.add_node(node['id'], label=node['label'],
                              shape=node['shape'], color=node['bordercolor'], style=node['style'], fillcolor=node['fillcolor'],
                              htmloutput=node['htmloutput'], extension=node['extension'])

        self.doc.add_comment('')
        return True

    def add_legend(self):
        """"""
        generationname_dict = {}
        # Read!
        if keys_exists(self.base, 'legendfile'):
            with open(self.base['legendfile'], 'r') as file_handle:
                generationname_dict = json.load(file_handle)
        # Write!
        # if keys_exists(self.base, 'legendfile'):
        #    with open(self.base['legendfile'], "w") as file_handle:
        #        file_handle.write(json.dumps(generationname_dict, indent=2))
        if not generationname_dict:
            return

        language = self.legend['language'].lower()
        fontsize_small = self.dot['font']['size'] -2
        fontstr_a = '<FONT POINT-SIZE="%s">(' % fontsize_small
        fontstr_b = ')</FONT>'
        for rel_key, rel_value in list(generationname_dict.items()):   # rel_ationship!
            for gen_key, gen_value in list(rel_value.items()):   # gen_eration!
                for k, v in list(gen_value.items()):
                    if '(' in v:
                        v = v.replace('(', fontstr_a).replace(')', fontstr_b)
                        generationname_dict[rel_key][gen_key][k] = v

        node = {'shape': 'box', 'style': '',
                'label': '\n    <TABLE border="0" cellspacing="1" cellpadding="5">\n',
                'bordercolor': '#FFFFFF', 'fillcolor': '#FFFFFF', 'fontcolor': '#000000',
                'htmloutput': True
               }

        male_color, female_color = '#000000', '#000000'
        if 'proband' in self.color and \
           ('male' in self.color['proband'] or 'female' in self.color['proband']):
            male_color = self.color['proband']['male']['fillcolor']
            female_color = self.color['proband']['female']['fillcolor']

        # Ascendents
        for generation in range(1, self.maxparents_generation):
            self.include_levelcolor(generation, node)
            node['label'] += '%s<TR><TD bgcolor="%s"><FONT COLOR="%s">%s</FONT></TD></TR>\n' % \
               (' '*6, node['fillcolor'], node['fontcolor'], generationname_dict['Ascendents'][str(generation)][language])

        # Probands
        node['label'] += '%s<TR><TD bgcolor="%s;0.5:%s;0.5">%s</TD></TR>\n' % \
           (' '*6, male_color, female_color, generationname_dict['Probands']['0'][language])

        # descendants
        for generation in range(1, self.maxchildren_generation):
            self.include_levelcolor(generation, node)
            node['label'] += '%s<TR><TD bgcolor="%s"><FONT COLOR="%s">%s</FONT></TD></TR>\n' % \
               (' '*6, node['fillcolor'], node['fontcolor'], generationname_dict['descendants'][str(generation)][language])

        node['label'] += '    </TABLE>'

        # we're done -- add the node
        self.doc.add_node('Legend', label=node['label'],
                          shape=node['shape'], color=node['bordercolor'], style=node['style'], fillcolor='#FFFFFF',
                          htmloutput=node['htmloutput'])

    # Filter for Kekule numbering
    def apply_kekule_filter(self, handle, generation):
        """"""
        if not handle: return
        if generation > self.maxparents_generations: return

        person = self.database.get_person_from_handle(handle)
        if not person.gramps_id in self.person_dict:
            ord_name = ordName(person)
            self.person_dict[person.gramps_id] = [generation, ord_name.shortname, handle]

        # Check for 'Stop' tags
        for tag_handle in person.tag_list:
            tag = self.database.get_tag_from_handle(tag_handle)
            if 'Stop' in tag.get_name(): return

        family_handle = person.get_main_parents_family_handle()
        if family_handle:
            family = self.database.get_family_from_handle(family_handle)
            self.apply_kekule_filter(family.get_father_handle(), generation +1)
            self.apply_kekule_filter(family.get_mother_handle(), generation +1)

    # Filter for Henry numbering
    def apply_henry_filter(self, handle, number, generation):

        if not handle: return
        if generation > self.maxchildren_generation: return

        # nur erwünschte ID's!
        person = self.database.get_person_from_handle(handle)
        if not person.gramps_id in self.person_dict:
            ord_name = ordName(person)
            self.person_dict[person.gramps_id] = [generation, ord_name.shortname, handle]
        else: return

        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)

            spouse_handle = utils.find_spouse(person, family)
            if spouse_handle:
                spouse = self.database.get_person_from_handle(spouse_handle)
                if spouse.gender == 1:   # Spouse = Male!
                    if not spouse.gramps_id in self.person_dict:
                        self.person_dict.pop(person.gramps_id,  None)   # Persone = Female, delete!

                        ord_name = ordName(spouse)
                        self.person_dict[spouse.gramps_id] = [generation, ord_name.shortname, spouse_handle]

                for child_ref in family.get_child_ref_list():
                    self.apply_henry_filter(child_ref.ref, generation +1)
