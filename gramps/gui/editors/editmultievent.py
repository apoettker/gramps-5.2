# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025   Alois Poettker
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

"""
Provide multiple event handling.
"""

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
from collections import defaultdict
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

import logging
_LOG = logging.getLogger(".editors.multievents")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.db import DbTxn
from gramps.gen.lib.date import Date, Today


from gramps.gen.lib import Citation, Date, Event, EventType, Media, \
     Note, Place, PlaceName, Source

#-------------------------------------------------------------------------
#
# EditMultiEvent
#
#-------------------------------------------------------------------------
class EditMultiEvent:
    """ """

    #----------------------------------------------------------------------
    def __init__(self, dbstate):
        """
        Create a new MultipleEvent instance as group of multiple single events
        """
        self.dbstate = dbstate.db
        self.default_objects = {}
        for obj in ['type', 'date', 'place', 'desc', \
                    'source', 'citation', 'note', 'media', 'attribute']:
            self.default_objects[obj] = None

    def __create_list(self, cursor, number):
        """ Loopup for existing elements, build a map"""
        element_list = defaultdict(list)
        data = next(cursor)
        while data:
            (handle, val) = data
            element_list[val[number]] = val[0]
            data = next(cursor)
        cursor.close()

        return element_list

    def _get_or_create_place(self, places):
        """Select or creates a new place called Multiple"""
        if not places:
            return None

        place_handle = places[0]
        if places[1:] != places[:-1]:
            place_names = self.__create_list(self.dbstate.get_place_cursor(), 2)
            if _("Multiple") not in place_names:
                place = Place()
                place.set_gramps_id("Pmult")
                place.set_title(_("Multiple"))
                place.set_name(PlaceName(value=_("Multiple")))
                with DbTxn(_("Initiate multiple Place"), self.dbstate) as trans:
                    self.dbstate.add_place(place, trans)
                self.default_objects['place'] = place.get_handle()
                place_handle = place.get_handle()
            else:
                place_handle = place_names[_("Multiple")]

        return place_handle

    def _get_or_create_source(self, sources):
        """Select or creates a new source called Multiple"""
        if not sources:
            return None

        source_handle = sources[0]
        if sources[1:] != sources[:-1]:
            source_titles = self.__create_list(self.dbstate.get_source_cursor(), 2)
            if _("Multiple") not in source_titles:
                source = Source()
                source.set_gramps_id("Smult")
                source.set_title(_("Multiple"))
                with DbTxn(_("Initiate multiple Source"), self.dbstate) as trans:
                    self.dbstate.add_source(source, trans)
                self.default_objects['source'] = source.get_handle()
                source_handle = source.get_handle()
            else:
                source_handle = source_titles[_("Multiple")]

        return source_handle

    def _get_or_create_citation(self, source_handle, citations):
        """Select or creates a new citation called Multiple"""
        if not citations:
            return None

        citation_handle = citations[0]
        if citations[1:] != citations[:-1]:
            citation_pages = self.__create_list(self.dbstate.get_citation_cursor(), 3)
            if _("Multiple") not in citation_pages:
                citation = Citation()
                citation.set_gramps_id("Cmult")
                citation.set_page(_("Multiple"))
                citation.set_date_object(Today())
                citation.set_reference_handle(source_handle)
                with DbTxn(_("Initiate multiple Citation"), self.dbstate) as trans:
                    self.dbstate.add_citation(citation, trans)
                self.default_objects['citation'] = citation.get_handle()
                citation_handle = citation.get_handle()
            else:
                citation_handle = citation_pages[_("Multiple")]

        return citation_handle

    def _get_or_create_note(self, notes):
        """Select or creates a new Note called Multiple"""
        if not notes:
            return None

        note_handle = notes[0]
        if notes[1:] != notes[:-1]:
            note_text = self.__create_list(self.dbstate.get_note_cursor(), 1)
            if _("Multiple") not in note_text:
                note = Note()
                note.set_gramps_id("Nmult")
                note.set(_("Multiple"))
                with DbTxn(_("Initiate multiple Notes"), self.dbstate) as trans:
                    self.dbstate.add_note(note, trans)
                self.default_objects['note'] = note.get_handle()
                note_handle = note.get_handle()
            else:
                note_handle = note_text[_("Multiple")]

        return note_handle

    def _get_or_create_media(self, medias):
        """Select or creates a new Media called Multiple"""
        if not medias:
            return None

        media_handle = medias[0]
        if medias[1:] != medias[:-1]:
            media_desc = self.__create_list(self.dbstate.get_media_cursor(), 2)
            if _("Multiple") not in media_desc:
                media = Media()
                media.set_gramps_id("Omult")
                media.set_description(_("Multiple"))
                with DbTxn(_("Initiate multiple Media"), self.dbstate) as trans:
                    self.dbstate.add_object(media, trans)
                self.default_objects['media'] = media.get_handle()
                media_handle = media.get_handle()
            else:
                media_handle = media_desc[_("Multiple")]

        return media_handle

    def get_events_from_handles(self, handles):
        """"""
        if not handles:
            return None

        date, place = None, None
        source, note, media, attribute = None, None, None, None

        elements = defaultdict(list)
        for handle in handles:
            event = self.dbstate.get_event_from_handle(handle)

            # Collect all Types
            elements["type"].append(event.get_type().value)

            # Collect all Dates
            date = event.get_date_object()
            elements["date"].append(date.get_sort_value())

            # Collect all Places
            place = event.get_place_handle()
            elements["place"].append(place)

            # Collect all Descriptions
            elements["desc"].append(event.get_description())

            # Collect all Citations
            citation_list = event.get_citation_list()
            if citation_list:
                for citation_handle in citation_list:
                    citation = self.dbstate.get_citation_from_handle(citation_handle)
                    source_handle = citation.source_handle
                    elements["source"].append(source_handle)
                    elements["citation"].append(citation_handle)

            # Collect all Notes
            note_list = event.get_note_list()
            if note_list:
                for note_handle in note_list:
                    elements["note"].append(note_handle)

            # Collect all Media
            mediaref_list = event.get_media_list()
            if mediaref_list:
                for mediaref in mediaref_list:
                    elements["media"].append(mediaref.ref)

            # Collect all Attribute
            attribute_list = event.get_attribute_list()
            if attribute_list:
                for attribute in attribute_list:
                    elements["attribute"].append(attribute.value)

        # Organize results
        for i in elements:
            elements[i].sort()   # Sorts entries
            elements[i] = list(set(elements[i]))   # Eliminates doubles

        # Create new Event with 'multiple' data
        event = Event()
        event.multiple = defaultdict(list)
        event.multiple['events'] = handles

        # Set (new) Type
        if elements["type"][1:] == elements["type"][:-1]:
            event.set_type(elements["type"][0])
        else:
            event.set_type((EventType.CUSTOM, _("Multiple")))
        event.multiple['type'] = str(event.type)

        # Set (new) Date
        if elements["date"][1:] != elements["date"][:-1]:
            date.set_as_text(_("Multiple"))
        event.set_date_object(date)
        event.multiple['date'] = event.date

        # Set (new) Place
        event.place = self._get_or_create_place(elements["place"])
        event.multiple['place'] = event.place

        # Set (new) Description
        description = elements["desc"][0]
        if elements["desc"][1:] != elements["desc"][:-1]:
            description = _("Multiple")
        event.set_description(description)
        event.multiple['desc'] = event.description

        # Set (new) Source / Citation
        source_handle = self._get_or_create_source(elements["source"])
        citation_handle = self._get_or_create_citation(source_handle, elements["citation"])
        if citation_handle:
            event.set_citation_list([citation_handle])

        # Set (new) Note
        note_handle = self._get_or_create_note(elements["note"])
        if note_handle:
            event.set_note_list([note_handle])

        # Set (new) Media
        media_handle = self._get_or_create_media(elements["media"])
        if media_handle:
            event.add_media_reference([media_handle])

        return event

    def clean_objects_from_multiple(self, obj):
        """"""
        with DbTxn(_("Delete multiple objects"), self.dbstate) as trans:
            if self.default_objects['place']:
                self.dbstate.remove_place(self.default_objects['place'], trans)
            if self.default_objects['source']:
                self.dbstate.remove_source(self.default_objects['source'], trans)
            if self.default_objects['citation']:
                self.dbstate.remove_citation(self.default_objects['citation'], trans)
            if self.default_objects['note']:
                self.dbstate.remove_note(self.default_objects['note'], trans)
            if self.default_objects['media']:
                self.dbstate.remove_media(self.default_objects['media'], trans)
