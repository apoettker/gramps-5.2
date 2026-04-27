# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025   Alois Poettker
#

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

from gramps.gen.db import DbTxn
from gramps.gen.lib import (Date,
                            Event, EventRef, EventRoleType, EventType,
                            )
from gramps.plugins.libAP.libbase import *
from gramps.plugins.moduleAP.completeplace import *

_DEBUG_ = False
_PRAEPOSITION_ = [' auch ', ' auf dem ', ' in ', ' zu ', ' zum ', ' zur ']   # ' ' vermeidet Worttrennungen

class CompleteEvent:
    """"""

    def __init__(self, database, substitute):
        """"""
        self.database = database
        self.substitute = substitute

        self.place = CompletePlace(database, substitute)

    def create_event_and_ref(self, type_, desc=None, date=None, place=None,
                               citation=None, note_text=None,
                               attr_text=None, attr_type=None, attr_cust=None):
        """
        Finds or creates an Event based on the Type, Description, Date, Place,
        Citation, Note and Time.
        """
        event = Event()
        event.set_type(EventType(type_))

        if date: event.set_date_object(date)
        if place: event.set_place_handle(place.get_handle())

        if not _DEBUG_:
            with DbTxn(_("Event creation"), self.database, batch=True) as trans:
                self.database.add_event(event, trans)   # add & commit ...

        event_ref = EventRef()
        event_ref.set_reference_handle(event.get_handle())

        return event, event_ref

    def find_specific_event(self, obj, event_type):
        """Determines a objects event due to event_type"""
        if not obj:
            return None

        event_found = None
        for event_ref in obj.get_event_ref_list():
            if event_ref.ref:
                event = self.database.get_event_from_handle(event_ref.ref)
                if event and (event.type.value == event_type):
                    event_found = event
                    break

        return event_found

    def sort_event_ref(self, person):
        """"""
        event_sort_list = []
        for event_ref in person.get_event_ref_list():
            if not event_ref.ref: continue
            event = self.database.get_event_from_handle(event_ref.ref)
            if not event: continue

            sortval = event.get_date_object().sortval
            if not sortval: sortval = 5000000   # Events w/o date

            # Absolute date justifing
            event_type = event.get_type().string
            if event_type == _('Birth'): sortval = 1   # Birth is always the Begin
            elif event_type == _('Baptism'): sortval = 2
            elif event_type == _('Christening'): sortval = 3
            elif event_type == _('Death'): sortval = 9999998
            elif event_type == _('Burial'): sortval = 9999999   # Burial is always the End

            event_sort_list.append([sortval, event_ref])

        event_sort_list.sort(key=lambda x: int(x[0]))

        event_ref_list = []
        for event_ref in event_sort_list:
            event_ref_list.append(event_ref[1])

        return event_ref_list

    def complete_event_christen(self, person, event):
        """"""
        # Ergänzung: Taufdatum
        event_change = False
        event_type = event.get_type().string
        if event_type == _('Birth'):
            if (event.date.modifier == Date.MOD_TEXTONLY) and \
               (u'(~' in event.date.text):
                # Berechnung "(~ dd.mm.yyyy)" in dd.mm.yyyy -1 Tag
                date_text = event.date.text.strip('(~').strip(')').strip()
                date, year, month, day = create_date_from_text(date_text)

                birth_year, birth_month, birth_day = year, month, day -1
                if birth_day == 0:
                    birth_month = (birth_month -1)
                    if birth_month < 1:
                        birth_month = 12
                        birth_year = birth_year -1
                    if birth_month == 2:
                        birth_day = 28
                    if birth_month in [4, 6, 9, 11]:
                        birth_day = 30
                    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
                        birth_day = 31

                if (birth_year > 0) or (birth_month > 0) or (birth_day > 0):
                    birth_date = Date(date)
                    birth_date.set_quality(Date.QUAL_ESTIMATED)
                    birth_date.set_yr_mon_day(birth_year, birth_month, birth_day)
                    event.set_date_object(birth_date)

                    christen_event_change = False
                    christen_event = self.find_specific_event(person, EventType.CHRISTEN)
                    if not christen_event:
                        christen_event = Event(source=event)
                        christen_event.set_gramps_id(self.database.find_next_event_gramps_id())
                        christen_event.set_handle(None)
                        christen_event.set_type(_('Christening'))
                        christen_event.set_date_object(date)

                        christen_event_change = True
                        print('  (~ Geburt) -> Geburt, Taufe')

                    reli_event = self.find_specific_event(person, EventType.RELIGION)
                    if reli_event:
                        handle_list = [reli_event.get_handle()]
                        person.remove_handle_references('Event', handle_list)
                        print('  -Religion')

                    with DbTxn(_("Birth completion"), self.database, batch=True) as trans:
                        if not _DEBUG_:
                            self.database.commit_event(event, trans)   # Birth-Event
                            if christen_event_change:
                                self.database.add_event(christen_event, trans)   # add & commit ...

                                event_ref = EventRef()
                                event_ref.set_role(EventRoleType.PRIMARY)
                                event_ref.set_reference_handle(christen_event.get_handle())
                                person.add_event_ref(event_ref)
                            if reli_event:
                                self.database.remove_event(reli_event.get_handle(), trans)
                            self.database.commit_person(person, trans)
                            event_change = True

        return event_change

    def complete_event(self, event, citation):
        """"""
        event_change = False
        subst_found, subst_desc = None, None
        event_type = event.get_type().string

        # Check: Date
        date = event.get_date_object()
        event.set_date_object(date)

        # Addition: Citation
        if citation and \
           citation not in event.citation_list:
            event.add_citation(citation)
            event_change = True

        # Substitution: Ort
        place_handle = event.get_place_handle()
        place = self.database.get_place_from_handle(place_handle) \
            if place_handle else None
        if place:
            place_name = place.get_name().value   # Debug!
            if (event_type == _('Baptism')) or (event_type == _('Christening')) or \
               (event_type == _('Marriage') and  event.date.get_year() < CIVIL_REGISTRY_YEAR) or \
               (event_type == _('Burial')):
                if self.substitute:
                    subst_found, subst_placename, subst_desc = \
                        self.substitute.compare_event(event, 'place', place)
                    if subst_found:
                        place = self.place.get_or_create_place(subst_placename)
                        event.set_place_handle(place.get_handle())
                        event_change = True
                        print('  Ort: %s -> %s' % (place_name, subst_placename))

        # Substitution: Beschreibung
        desc = event.get_description()
        if subst_found:
            """
            # Ergänzung Description
            subst_placename = subst_placename.replace(',', '').replace(';', '')
            for element in subst_placename.split(' '):
                if element in desc:
                    desc = desc.replace(element, '')
            """
            if subst_desc:
                # desc = '%s %s' % (subst_desc, desc)
                event.set_description(subst_desc.strip())
                event_change = True
                print('  Desc: %s -> %s' % (desc, subst_desc))

        # Aufspaltung: Beruf
        if event_type == _('Occupation'):
            description = event.get_description()
            for praeposition in _PRAEPOSITION_:
                if praeposition in description:
                    desc = description.replace('und', '&')
                    # ??? desc = description.person.add_citation(citation.handle).split(praeposition, 1)
                    if desc:
                        event.set_description(desc[0].strip())
                    place = self.place.get_or_create_place(desc[1].strip())
                    if place:
                        event.set_place_handle(place.get_handle())
                        event_change = True
                        placename = place.get_name().value   # Debug!
                        print('  Beruf: %s >> %s' % (desc[0], placename))
                    break

        # Umwandlung: Heirat -> Trauung
        if event_type == _('Marriage'):
            if (event.date.get_year() < FRANCE_YEAR_LOW) or \
               (FRANCE_YEAR_HIGH < event.date.get_year() < CIVIL_REGISTRY_YEAR):
                event.type.value = EventType.CUSTOM
                event.type.string = 'Trauung'
                event_change = True

        if not _DEBUG_ and event_change:
            with DbTxn(_("Event completion"), self.database, batch=True) as trans:
                self.database.commit_event(event, trans)
                # print('  Event saved.')

        return event_change
