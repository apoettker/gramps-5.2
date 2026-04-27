# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2022   Alois Poettker
#

"""Tools/Database Processing/Extract Event Descriptions from Event Data"""

_DEBUG_ = False

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import os, re

from os.path import expanduser

# from anytree import Node, RenderTree, PreOrderIter, search, util

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

from gramps.gen.db import DbTxn
from gramps.gui.plug import tool

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libnameobject import ordName

from gramps.plugins.libAP.libsubstobject import SubstitutionParser
from gramps.plugins.moduleAP.completenames import *
from gramps.plugins.moduleAP.completeperson import *
from gramps.plugins.moduleAP.completefamily import *

#-------------------------------------------------------------------------
#
# variables
#
#-------------------------------------------------------------------------

class CompleteObjects(tool.BatchTool):
    """"""
    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.dbstate = dbstate
        self.database = dbstate.db

        self.default_dataset()
        self.read_dataset(options_class)

        self.substitute = None
        if keys_true(self.base, 'substitute', 'enable'):
            self.substitute = SubstitutionParser()
            self.substitute.import_data(self.base['substitute']['file'])

        self.begin_report()

        return None

    def default_dataset(self):
        """"""
        self.base = {}
        self._base = {
            "database_file": '',

            "substitution": {"enable": False,
                "file": '',
                "instance": None,
            },
            "analyze": {"enable": False,
                "file": '',
                "handle": None,
                "list": '',
            },
        }

        self.csv_import = {}
        self._csv_import = {
            "enable": False,
            "import_file_IND": '',
            "import_file_FAM": ''
        }

        self.citation = {}
        self._citation = {
            "enable": False,
            "export_date": '',
            "export_type":  '',
            "export_file": '',
        }

        self.source = {}
        self._source = {
            "enable": False,
            "source_id": ''
        }

        self.person = {}
        self._person = {"enable": False,
            "number": {
                "enable": False,
                "mode": '',
                "followparents": False,
                "followchildren": False,

                "person-id": 'I00000',
                "start-id": 'I00000',
                "protect": {
                    "enable": False,
                    "begin-id": 'I00000',
                    "end-id": 'I00000'
                },

                "analyze": {"enable": False,
                    "file": '',
                },
            },

            "name": {"enable": False,
                "callname_estimation": False,
                "nametype_enforcement": '',

                "analyze": {"enable": False,
                    "file": '',
                },
            },

            "analyze": {"enable": False,
                "file": '',
            },
        }

        self.family = {}
        self._family = {"enable": False,
            "name": {"enable": False,
                "analyze": {"enable": False,
                    "file": '',
                },
                "groupname_enforcement": False
            },

            "analyze": {"enable": False,
                "file": '',
            },
        }

        self.cleanup = {}

        return None

    def read_dataset(self, options):
        """"""
        if 'data_set' in options.options_dict:
            file_name = options.options_dict['data_set']
            if file_name[-3:] != ".js": file_name += ".js"
            with open(file_name, 'r') as self.data_handle:
                dataset = json.load(self.data_handle)

        {setattr(self, key, value) for (key, value) in dataset.items()}

        self.base = {**self._base, **self.base}

        if 'csv_import' in dataset:
            self.csv_import = {**self._csv_import, **self.csv_import}

        if 'person' in dataset:
            self.config_person = {**self._person, **self.person}

        if 'family' in dataset:
            self.config_family = {**self._family, **self.family}

        if 'source' in dataset:
            self.source = {**self._source, **self.source}

        if 'citation' in dataset:
            self.citation = {**self._citation, **self.citation}
            self.citation['export_prevalue'] = '%s %s' % (self.citation['export_type'], self.citation['export_date'])

        return None

    def begin_report(self):
        """
        This is where we'll do all of the work of figuring out who
        from the database is going to be output into the report
        """
        self.analyse = AnalyzeFile(self.base['analyze'])

        if keys_true(self.config_person, 'enable'):
            persons = CompletePerson(self.database, self.substitute, self.config_person)

            if keys_true(self.config_person, 'number', 'enable'):
                persons.complete_person_number()

            if keys_true(self.config_person, 'name', 'enable'):
                personsname = CompletePersonName(self.database, self.substitute, self.config_person)

                if keys_true(self.config_person, 'name', 'groupname_enforcement'):
                    persons.complete_person_groupname()
                else:
                    personsname.complete_person_name()

            if keys_true(self.config_person, 'objects', 'enable'):
                persons.complete_person()

        if keys_true(self.config_family, 'enable'):
            families = CompleteFamily(self.database, self.substitute, self.config_family)

            if keys_true(self.config_family, 'number', 'enable'):
                families.complete_family_number()

            if keys_true(self.config_family, 'name', 'enable'):
                if keys_true(self.config_family, 'name', 'groupname_enforcement'):
                    families.complete_mate_groupname()

            if keys_true(self.config_family, 'objects', 'enable'):
                families.complete_family()

    def complete_import(self):

        # == ***A.gramps Datenbank

        # self.complete_person_name()
        # -> ***B.gramps Datenbank

        # self.complete_source()
        # self.create_citation_perfam()
        # self.complete_citation_event()
        # -> ***C.gramps Datenbank

        # self.reorganise_place()
        # self.complete_person()
        # -> ***D.gramps Datenbank

        # self.complete_family()
        # -> ***E.gramps Datenbank

        # One-Time
        # self.compact_source()
        # self.compact_citation()
        # self.modify_citation()
        # self.complete_citation_perfam()
        # self.complete_citation_memoriamcard()
        # self.complete_memoriamcard()

        # self.person_dict, self.family_dict = {}, {}
        # self.create_person()
        # self.__create_person_map()
        # self.__create_family_map()
        # self.create_family()

        pass

#------------------------------------------------------------------------
    def complete_memoriamcard(self):
        self.citation_attribute = 'Totenzettel Gerdes, Elisabeth 2013-08-31'

        """ Perform the completion of Persons. """
        umlauteINTtoDE = {   # German Umlauts to International
            u'Ae' : u'Ä', u'ae' : u'ä',
            u'Oe' : u'Ö', u'oe' : u'ö',
            u'Ue' : u'Ü', u'ue' : u'ü',
            u'ss' : u'ß'
        }
        umlauteDEtoINT = {   # International to German Umlauts
            u'Ä' : u'Ae', u'ä' : u'ae',
            u'Ö' : u'Oe', u'ö' : u'oe',
            u'Ü' : u'Ue', u'ü' : u'ue',
            u'ß' : u'ss'
        }

        person_idx = 0
        self.database.disable_signals ()

        base_citation = self.database.get_citation_from_gramps_id('C00000')

        person_handle_list = list (self.database.iter_person_handles())
        for person_handle in person_handle_list:

            # Zielextraktion
            person = self.database.get_person_from_handle(person_handle)
            if person is None:
                continue

            if person.get_citation_list():
                citation_handle = person.get_citation_list()[0]
            else:
                continue
            if citation_handle:
                citation = self.database.get_citation_from_handle(citation_handle)
            else:
                continue

            person_idx += 1
            # if person_idx == 11: break

            pers_name = ordName(person, mode='C')   # C: Complete Objects
            death_date = citation.date.dateval[2]

            description = '%s Totenzettel %s, %s %s' % \
                (person.gramps_id, pers_name.surname, pers_name.givenname, death_date)
            verzeichnis = '%s %s, %s' % \
                (person.gramps_id, pers_name.surname, pers_name.givenname)
            for char in umlauteDEtoINT:
                verzeichnis = verzeichnis.replace(char, umlauteDEtoINT[char])
            dateiname = '%s TZ %s, %s %s' % \
                (person.gramps_id, pers_name.surname, pers_name.givenname, death_date)
            for char in umlauteDEtoINT:
                dateiname = dateiname.replace(char, umlauteDEtoINT[char])
            relativpfad = 'IND/11xxx/%s/%s' % (verzeichnis, dateiname)

            # Medienerstellung
            for char in umlauteINTtoDE:
                description = description.replace(char, umlauteINTtoDE[char])

            mediaA, mediaB = Media(), Media()

            mediaA.set_mime_type('image/jpeg')
            mediaA.set_description('%s A' % description)
            mediaA.set_date_object(citation.date)
            mediaA.set_path('%s A.jpg' % relativpfad)
            mediaA.set_citation_list([base_citation.handle])

            mediaB.set_description('%s B' % description)
            mediaB.set_mime_type('image/jpeg')
            mediaB.date = citation.date
            mediaB.set_path('%s B.jpg' % relativpfad)
            mediaB.set_citation_list([base_citation.handle])

            with DbTxn(_("Media completion"), self.database, batch=True) as trans:
                if not _DEBUG_:
                    if not mediaA.get_handle():
                        self.database.add_object(mediaA, trans)
                    if not mediaA.get_gramps_id():
                        mediaA.set_gramps_id(self.database.find_next_object_gramps_id())
                    self.database.commit_media_object(mediaA, trans)

                    if not mediaB.get_handle():
                        self.database.add_object(mediaB, trans)
                    if not mediaB.get_gramps_id():
                        mediaB.set_gramps_id(self.database.find_next_object_gramps_id())
                    self.database.commit_media_object(mediaB, trans)

            # Dateierstellung
            home = expanduser("~")
            directory = '%s/M/IND/11xxx/%s' % (home, verzeichnis)
            if not os.path.exists(directory):
                os.makedirs(directory)

            mediaApfad = '%s/M/%s A.jpg' % (home, relativpfad)
            if not os.path.exists(mediaApfad):
                fileA = open(mediaApfad, 'w')
                fileA.close()
            mediaBpfad = '%s/M/%s B.jpg' % (home, relativpfad)
            if not os.path.exists(mediaBpfad):
                fileB = open(mediaBpfad, 'w')
                fileB.close()

            # Medienreferenzerstellung
            mediaAref, mediaBref = MediaRef(), MediaRef()

            mediaAhandle = mediaA.get_handle()
            if mediaAhandle:
                mediaAref.set_reference_handle(mediaAhandle)
            mediaBhandle = mediaB.get_handle()
            if mediaBhandle:
                mediaBref.set_reference_handle(mediaBhandle)

            # Ereignisergänzung
            imc_event = None   # In Memoriam Card Event
            for event_ref in person.get_event_ref_list():
                event = self.database.get_event_from_handle(event_ref.ref)
                if event is None:
                    continue

                event_type = event.get_type().value
                # Type 13: Death, 19: Burial
                if event_type == 13:
                    imc_event = event
                if event_type == 19:
                    imc_event = event
                    break
                pass

            if imc_event:
                mediaAref.set_citation_list([citation_handle])
                mediaBref.set_citation_list([citation_handle])

                imc_event.add_media_reference(mediaAref)
                imc_event.add_media_reference(mediaBref)

                with DbTxn(_("Event completion"), self.database, batch=True) as trans:
                    if not _DEBUG_:
                        self.database.commit_event(imc_event, trans)

            # Verweisergänzung
            if mediaAhandle or mediaBhandle:
                citation.set_media_list([mediaAref, mediaBref])

                with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
                    if not _DEBUG_:
                        self.database.commit_citation(citation, trans)

            print("%i: %s" % (person_idx, description))

        self.database.enable_signals()
        self.database.request_rebuild()

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
class CompleteObjectsOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """
    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)
        self.options_dict['data_set'] = ''
