# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025   Alois Poettker
#

"""Tools/Database Processing Person Completion"""

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

from gramps.gen.db import DbTxn
from gramps.gen.lib import (Family, FamilyRelType,
                            Name, AttributeType)

from gramps.gen.utils.id import create_id

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libnameobject import *
from gramps.plugins.moduleAP.completeevents import *

_DEBUG_ = True

class CompleteFamily:

    def __init__(self, database, substitute, config):
        """"""
        self.database = database
        self.substitute = substitute
        self.config = config

        self.person_dict, self.family_dict = {}, {}

    def __create_family_map(self):
         # look for existing family titles, build a map
        print('Building Family Map ...')
        self.family_names = defaultdict(list)
        cursor = self.database.get_family_cursor()
        data = next(cursor)
        while data:
            (handle, val) = data
            father_name, mother_name = 'N.N.', 'N.N.'
            if val[2]:
                father = self.database.get_person_from_handle(val[2])
                father_name = father.get_primary_name().get_surname()
            if val[3]:
                mother = self.database.get_person_from_handle(val[3])
                mother_name = mother.get_primary_name().get_surname()
            gen = int(val[8][1][4]) if val[8] else -1
            key = '%s=%s' % (father_name, mother_name)
            self.family_dict[key] = {'gen': gen, 'pid': val[1], 'father': val[2], 'mother': val[3], 'handle': handle}
            data = next(cursor)
        cursor.close()

    def __find_or_create_family(self, source, fid, gen, fathername, mothername, mdate=None, mplace=None):
        """ Finds or creates a Family based on the ID. """
        _NameSubstitute_ = {
          # 'Child':  (Gen, 'Father / Mother')
            'Benes' : (0, 'Kramer'),
            'Behnes' :  (3, 'Benes'),
            'Borchorst': (4, 'zur Horst'),
            'Breimann': 'Breymann',
            'Claessen': 'Claes',
            'Cordes': 'Coers',
            'Dumstorpf': 'Dumpstrup',
            'Fehr': 'Zurfehr',
            'Frerecks': 'Freericks',
            'Vriesemann': (4, 'Fresemann'),
            'Fryen': 'Frye',
            'Funcke': 'Funke',
            'Garrelmann': 'Garlmann',
            'Jansen': 'Jansing',
            'Janssen': 'Janhsen',
            'Jöne': 'Jänen',
            'Heiken': 'Heycken',
            'Klasen': 'Klaas',
            'Lücken': (4, 'Leffers'),
            'Möller': 'Müller',
            'Oldigs': 'Oldiges',
            'Rolefes': 'Rolfes',
            'Schnieder': 'Schnieders',
            'Sinnigen': 'Sinningen',
            'Suering': 'Timann',
            'Tiemanns': 'Soring',
            'Langen': (4, 'von Langen'),
            'Vorthermes': 'Vortherms',
            'Wehseling': 'Wesseling',
            'Wesseling': 'Weßling',
            'Wermelts': 'Wermes',
            'Wülfer': 'Wülfer',
            'Würtz': 'Wurth',
            'zur Horst': 'Horst',
            'zum Sande': 'Zumsande',
        }
        # check for matching surnames


        success = False
        childname = ''
        for gender in self._GenderSet_:
            nid = 'IND-%s:%s' % (fid, gender)
            if nid in self.person_dict:
                childname = self.person_dict[nid]['name'].split(',')[0]

                if fathername == 'N.N':
                    success = True
                elif fathername != childname:
                    if childname in _NameSubstitute_ and _NameSubstitute_[childname][1] == fathername:
                        fathername = childname
                        success = True
                    elif mothername == childname:
                        success = True
                else: success = True

                if success: break

        if not success:
            return 'nil', None, childname

        # check for full existence
        key = '%s=%s' % (fathername, mothername)
        if key in self.family_dict and gen == self.family_dict[key]['gen']:
            family = self.database.get_family_from_handle(self.family_dict[key]['handle'])

            return 'old', family, ''

        # create a new Family
        family = Family()
        gramps_id = self.database.find_next_family_gramps_id()
        family.set_gramps_id(gramps_id)
        handle = create_id()
        family.set_handle(handle)

        family_attr = self.__create_attribute(source + nid, AttributeType.ID)
        if family_attr: family.add_attribute(family_attr)

        family_attr = self.__create_attribute(str(gen), AttributeType.CUSTOM, "Generation")
        if family_attr: family.add_attribute(family_attr)

        if mdate or mplace:
            marriage_date, __, __, __ = create_date_from_text(mdate)
            marriage_place = self.__get_or_create_place(mplace)
            __, marriage_ref = self.__create_event_and_ref(EventType.MARRIAGE, date=marriage_date, place=marriage_place)
            if marriage_ref: family.add_event_ref(marriage_ref)

        return 'new', family, ''

    def create_family(self):
        _DataAmount_ = 333
        _GenderSet_ = ('F', 'M', 'U')

        """ Perform the creation of Families. """
        self.database.disable_signals()

        analyse_list = []
        analyse_list.append('Processing %s file ...' % self.csv_import['import_file_FAM'])

        data = open_file(self.csv_import['import_file_FAM'], 'csv')
        if not data: return None

        fid = 0
        family_start, family_stop = 00 +7, self._DataAmount_   #  7: Leerzeilen

        with DbTxn(_("Family creation"), self.database, batch=True) as self.trans:
            for row_number, row in enumerate(data[family_start:], start=(family_start)):
                if row_number > family_start + family_stop -1: break
                if row[0] and row[0][0] == '#': continue   # comment lines starts with '#'
                if (row[1] == '[privacy]' and row[2] == '[privacy]') or  \
                   (row[1] == '' and row[2] == '[privacy]') or \
                   (row[1] == '[privacy]' and row[2] == '') or  \
                   (row[1] == '' and row[2] == ''): continue

                if row[0] in ['IV.43']:
                    a = 1

                child_exist = False
                for gender in _GenderSet_: # Child (checked by NID)
                    nid = 'IND-%s:%s' % (row[0], gender)
                    if nid in self.person_dict:
                        child_exist = True
                        break

                father_exist = True if row[1] != '' else False   # Father
                mother_exist = True if row[2] != '' else False   # Mother
                if father_exist or mother_exist:
                    gen = roman.fromRoman(row[0].split('.')[0])   # converting roman generation number to integer
                    father_name = row[1].split(',')[0] if father_exist and row[1] != '[privacy]' else ''
                    mother_name = row[2].split(',')[0] if mother_exist and row[2] != '[privacy]' else ''

                    # gen -1: looking for Parents!
                    state, family, desc = self.__find_or_create_family('FAM-', row[0], gen -1, father_name, mother_name)
                    if not family:
                        print('   -> Fam: %s: %s != %s' % (row[0], father_name, desc))
                        analyse_list.append('   -> Fam: %s: C:%s != P:(%s / %s)' % (nid, desc, father_name, mother_name))
                        continue

                    if state == 'new':
                        if row[1] != '[privacy]':
                            __, father = self._create_or_update_person(source='FAM:M-', nid=row[0], gen=gen -1, \
                                                                      name=row[1], gender='M')
                            family.set_father_handle(father.handle)
                            father.add_family_handle(family.get_handle())

                            if not _DEBUG_: self.database.commit_person(father, self.trans)

                        if row[2] != '[privacy]':
                            __, mother = self._create_or_update_person(source='FAM:F-', nid=row[0], gen=gen -1, \
                                                                      name=row[2], gender='F')
                            family.set_mother_handle(mother.handle)
                            mother.add_family_handle(family.get_handle())

                            if not _DEBUG_: self.database.commit_person(mother, self.trans)

                        if not _DEBUG_:   # add & commit ...
                            self.database.commit_family(family, self.trans)

                        key = '%s=%s' % (father_name, mother_name)
                        self.family_dict[key] = {'gen': gen -1, 'handle': family.handle}

                    if child_exist:
                        # check for double child reference
                        child_handle = self.person_dict[nid]['handle']
                        family_childref = family.get_child_ref_list()
                        reference = any(ref.ref == child_handle for ref in family_childref)
                        if reference: continue

                        childref = ChildRef()
                        childref.set_reference_handle(child_handle)
                        family.add_child_ref(childref)

                        child = self.database.get_person_from_handle(child_handle)
                        child.add_parent_family_handle(family.get_handle())

                    if not _DEBUG_:   # add & commit ...
                        if child_exist: self.database.commit_person(child, self.trans)
                        self.database.commit_family(family, self.trans)

                    fid += 1
                    print('%4i. Fam: %s: %s -- %s [%s]' % (fid, row[0], father_name, mother_name, family.gramps_id))
                    analyse_list.append('%4i. Fam: %s: %s -- %s [%s]' % \
                                        (fid, row[0], father_name, mother_name, family.gramps_id))

        if self.base['analyze_file']:
            for analyze in analyse_list: self.analyze_handle.write('%s\n' % analyze)
            self.analyze_handle.write('\n')

        self.database.enable_signals()
        self.database.request_rebuild()

        return None

# ============================================================================================================================ #

    def complete_family_name(self, family, father, mother):
        """ Perform the completion of married persons Names. """
        if not father or not mother:
            return None

        father_name = father.get_primary_name()
        mother_name = mother.get_primary_name()

        base_name = None
        break_reason = ''
        for name in mother.get_alternate_names():
            name_type = name.get_type().value
            if name_type == NameType.BIRTH:
                base_name = name
                break_reason = NameType.BIRTH
                break
            if name_type == NameType.MARRIED:
                break_reason = NameType.MARRIED
                break
        if break_reason == NameType.MARRIED:
            return None

        if not base_name:
            base_name = mother_name

        if father_name.surname_list[0]:
            family_name = Name(base_name)
            family_name.set_type(NameType.MARRIED)

            del family_name.surname_list[:]
            family_name.surname_list.append(father_name.surname_list[0])

            # Citation
            citation = family.get_citation_list()[0] \
                if family.get_citation_list() else None
            del family_name.citation_list[:]
            if citation: family_name.add_citation(citation)

            # Date
            wedding, __ = find_specific_event \
                (self.database, family, [EventType.CUSTOM], eventtyestring='Trauung', roletypelist=[EventRoleType.FAMILY])
            if wedding: family_name.date = Date(wedding.date)

            marriage, __ = find_specific_event \
                (self.database, family, [EventType.MARRIAGE], roletypelist=[EventRoleType.FAMILY])
            if marriage: family_name.date = Date(marriage.date)

            if mother.gramps_id == 'I00343':
                a = 1
            mother.add_alternate_name(family_name)

            if not _DEBUG_:
                with DbTxn(_("Name completion"), self.database, batch=True) as trans:
                    self.database.commit_person(mother, trans)

        return None

    def complete_family(self):
        """ Perform the completion of Families. """

        self.analyse = AnalyzeFile(self.config['name']['analyze'])
        self.analyse.start()

        # self.event = CompleteEvent(self.database, self.substitute)

        family_dict = {}
        family_handle_list = list(self.database.iter_family_handles())
        family_start, family_stop = 0, 999
        for family_idx, family_handle in enumerate(family_handle_list[family_start:], start = family_start):
            if family_idx > family_start + family_stop: break
            family = self.database.get_family_from_handle(family_handle)
            if family is None: continue

            father, mother = None, None
            father_surname, mother_surname = 'N.N.', 'N.N.'
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                father_surname = ordName(father).surname
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                mother_surname = ordName(mother).surname

            fgramps_id = 'F' + family.gramps_id[1:].zfill(5)
            print("Fam %s: [%s] %s -- %s" % (family_idx, fgramps_id, \
                                             father_surname, mother_surname))

            """
            for event_ref in family.event_ref_list:
                val = event_ref.role.value
                # string = event_ref.role.string   # Debug!
                if val == 1:   # 1: Primär
                    event_ref.set_role(8)   # 8: Familie

            relationship = family.get_relationship()
            if relationship != FamilyRelType.MARRIED:
                family.set_relationship(FamilyRelType.MARRIED)
            self.complete_family_name(family, father, mother)

            # Citation
            citation = family.get_citation_list()[0] \
               if family.get_citation_list() else ''

            # Events
            for event_ref in family.get_event_ref_list():
                if not event_ref.ref: continue
                event = self.database.get_event_from_handle(event_ref.ref)
                if not event: continue

                # Citation, Place, Occupation Event
                self.event.complete_event(event, citation)
            """

            family_dict[family_idx] = family

        self.database.disable_signals ()
        if not _DEBUG_ and len(family_dict) > 0:
            with DbTxn(_("Family completion"), self.database, batch=True) as trans:
                for value in family_dict.values():   # 0: Family
                    self.database.commit_family(value, trans)
        self.analyse.stop()

        self.database.enable_signals()
        self.database.request_rebuild()


    def complete_family_number(self):
        """"""
        _debug_ = True

        self.analyze = AnalyzeFile(self.config['number']['analyze'])
        self.analyze.start()

        family_dict = {}
        family_start = int(self.config['number']['source_start-id'][1:])
        family_stop = int(self.config['number']['source_stop-id'][1:]) +1
        for cnt, fid in enumerate(range(family_start, family_stop)):
            if cnt > family_start + family_stop: break
            family_id = 'F' + str(fid).zfill(4)
            family = self.database.get_family_from_gramps_id(family_id)
            if family is None: continue

            father, mother = None, None
            father_name, mother_name = 'N.N.', 'N.N.'
            if family.father_handle:
                father = self.database.get_person_from_handle(family.father_handle)
                father_name = father.get_primary_name().get_surname()
            if family.mother_handle:
                mother = self.database.get_person_from_handle(family.mother_handle)
                mother_name = mother.get_primary_name().get_surname()
            family_name = '%s -- %s' % (father_name, mother_name)

            family_dict[cnt] = {'fid': family_id, 'name': family_name, 'object': family, \
                                'father_name': father_name, 'father': father,
                                'mother_name': mother_name, 'mother': mother}

        self.database.disable_signals ()
        with DbTxn(_("Family completion"), self.database, batch=True) as trans:
            for fid, fam in enumerate(family_dict):
                if keys_true(self.config, 'number', 'shift', 'enable'):
                    family = family_dict[fam]['object']
                    family_start = int(self.config['number']['shift']['target_start-id'][1:])
                    family.gramps_id = 'F' + str(family_start + fid)

                    self.analyze.append('%s -> %s: %s' % \
                        (family_dict[fam]['fid'], family.gramps_id, family_dict[fam]['name']))

                    if not _debug_:
                        self.database.commit_family(family, trans)

                if keys_true(self.config, 'number', 'twist', 'enable'):
                    father_id, mother_id = 0, 0
                    if family_dict[fam]['father']: father_id = int(family_dict[fam]['father'].gramps_id[1:])
                    if family_dict[fam]['mother']: mother_id = int(family_dict[fam]['mother'].gramps_id[1:])
                    if father_id == 0 or mother_id == 0: continue

                    # Father ID == Odd & Mother ID == Even
                    if (father_id % 2 == 1) and (mother_id % 2 == 0):
                       # and abs(father_id - mother_id) == 1:
                        self.analyze.append('%s %s: %s %s -- %s %s' % \
                            (family_dict[fam]['fid'], family_dict[fam]['name'], \
                             family_dict[fam]['father'].gramps_id, family_dict[fam]['father_name'], \
                             family_dict[fam]['mother'].gramps_id, family_dict[fam]['mother_name']))

                        if not _debug_:
                            if family_dict[fam]['father']:
                                family_dict[fam]['father'].gramps_id = 'I' + str(mother_id).zfill(5)
                                self.database.commit_person(family_dict[fam]['father'], trans)
                            if family_dict[fam]['mother']:
                                family_dict[fam]['mother'].gramps_id = 'I' + str(father_id).zfill(5)
                                self.database.commit_person(family_dict[fam]['mother'], trans)

        self.analyze.stop()
        self.database.enable_signals()
        self.database.request_rebuild()

        return

    def complete_mate_groupname(self):
        """"""
        _debug_ = True

        def complete_groupname(personname, mate, nametype):
            """"""
            success = False
            mate_altnames = mate.get_alternate_names()
            for altname in mate_altnames:
                if altname.get_type().value == nametype:
                    altname.group_as = personname.groupname
                    self.person_dict[mate.gramps_id] = {'handle': val[3], 'altnames': mate_altnames}
                    success = True
            return success

        print("Complete Mate's Groupname ...")

        self.analyze = AnalyzeFile(self.config['name']['analyze'])
        self.analyze.start()

        cursor = self.database.get_family_cursor()
        data = next(cursor)
        i = 1
        while data:
            (handle, val) = data
            father_name, mother_name = None, None
            if val[2]:
                father = self.database.get_person_from_handle(val[2])
                father_name = ordName(father)
            if val[3]:
                mother = self.database.get_person_from_handle(val[3])
                mother_name = ordName(mother)

            if father_name and father_name.groupname:
                if mother_name and \
                   (father_name.lastname == mother_name.marriagename):
                    # complete_groupname(father_name, mother, NameType.MARRIED)
                    success = complete_groupname(father_name, mother, NameType.AKA)
                    if success:
                        self.analyze.append('%s %s:: [%s] Pers: %s!%s [%s] Mate: %s -> Mate: %s!%s' % \
                            (i, val[1], father.gramps_id, father_name.groupname, father_name.lastname, \
                             mother.gramps_id, mother_name.marriagename, father_name.groupname, mother_name.marriagename))

            if mother_name and mother_name.groupname:
                if father_name and \
                    (mother_name.lastname == father_name.marriagename):
                    # complete_groupname(mother_name, father, NameType.MARRIED)
                    success = complete_groupname(mother_name, father, NameType.AKA)
                    if success:
                        self.analyze.append('%s %s:: [%s] Pers: %s!%s [%s] Mate: %s -> Mate: %s!%s' % \
                            (i, val[1], mother.gramps_id, mother_name.groupname, mother_name.lastname,
                             father.gramps_id, father_name.marriagename, mother_name.groupname, father_name.marriagename))

            data = next(cursor)
            i += 1
        cursor.close()
        self.analyze.stop()

        self.database.disable_signals()
        if len(self.person_dict) > 0:
            with DbTxn(_("Mate's Groupname completion"), self.database, batch=True) as trans:
                for key, value in self.person_dict.items():   # 0: Person
                    person = self.database.get_person_from_handle(value['handle'])
                    person.alternate_names = value['altnames']
                    if not _debug_:
                        self.database.commit_person(person, trans)   # add & commit ...
        self.database.enable_signals()
        self.database.request_rebuild()

        return
