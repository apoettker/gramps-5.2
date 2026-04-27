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
from gramps.gen.lib import (Person)

from gramps.gen.plug.report import utils
from gramps.gen.utils.id import create_id

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libobjects import *
from gramps.plugins.libAP.libnameobject import *
from gramps.plugins.moduleAP.completeevents import *

class CompletePerson:

    def __init__(self, database, substitute, config):
        """"""
        self.database = database
        self.substitute = substitute
        self.config = config
        self.statistik = {'fnMale': 0, 'fnFemale': 0}   # false numbering {Male, Female}

        self.person_dict, self.target_dict = {}, {}

    def create_person_map(self, mode='all', pid='I00000'):
        # look for existing person titles, build a map

        def create_parent_relation(person):
            """"""
            fid, mid = None, None

            for parent_handle in person.get_parent_family_handle_list():
                parent = self.database.get_family_from_handle(parent_handle)
                if parent:
                    father_handle = parent.get_father_handle()
                    if father_handle:
                        father = self.database.get_person_from_handle(father_handle)
                        if father:
                            fid = father.get_gramps_id()
                            if not fid in self.person_dict:
                                self.person_dict[fid[1:]] = {'name': father.primary_name.get_name(), 'pid': fid, 'handle': father.handle}

                    mother_handle = parent.get_mother_handle()
                    if mother_handle:
                        mother = self.database.get_person_from_handle(mother_handle)
                        if mother:
                            mid = mother.get_gramps_id()
                            if not mid in self.person_dict:
                                self.person_dict[mid[1:]] = {'name': mother.primary_name.get_name(), 'pid': mid, 'handle': mother.handle}
            return fid, mid

        def create_spouse_relation(person, family):
            # include the spouse from this person's family
            spouse_handle = utils.find_spouse(person, family)
            if spouse_handle:
                spouse = self.database.get_person_from_handle(spouse_handle)
                spid = spouse.gramps_id
                if not spid in self.person_dict:
                    self.person_dict[spid[1:]] = {'name': spouse.primary_name.get_name(), 'pid': spid, 'handle': spouse.handle}

                if spouse.parent_family_list:
                    create_parent_relation(spouse)
            return

        def create_children_relation(family, recursive=True):
            """"""
            for child_ref in family.get_child_ref_list():
                child = self.database.get_person_from_handle(child_ref.ref)
                cid = child.get_gramps_id()
                if child.get_family_handle_list() and recursive:
                    self.create_person_map('group', cid)
                else:
                    if not cid in self.person_dict:
                        self.person_dict[cid[1:]] = {'name': child.primary_name.get_name(), 'pid': cid, 'handle': child.handle}
            return

        def create_reference_relation(person):
            # iterate through this person's references
            for person_ref in person.get_person_ref_list():
                reference = self.database.get_person_from_handle(person_ref.ref)
                rid = reference.get_gramps_id()
                if not rid in self.person_dict:
                    self.person_dict[rid[1:]] = {'name': reference.primary_name.get_name(), 'pid': rid, 'handle': reference.handle}
            return

        print('Building Person Map ...')

        if mode == 'all':
            cursor = self.database.get_person_cursor()
            data = next(cursor)
            i = 0
            while data:
                person = self.database.get_person_from_handle(data[0])
                pid = person.gramps_id
                if person:
                    if not (pid in self.person_dict):
                        self.person_dict[pid[1:]] = {'name': person.primary_name.get_name(), 'pid': pid, 'handle': data[0]}
                data = next(cursor)
                i += 1
            cursor.close()

        if mode == 'group':
            person = self.database.get_person_from_gramps_id(pid)
            if person:
                if not (pid in self.person_dict):
                    self.person_dict[pid[1:]] = {'name': person.primary_name.get_name(), 'pid': person.gramps_id, 'handle': person.handle}

                if self.config['number']['followparents']:
                    if person.parent_family_list:
                        # iterate through this person's parent families
                        for family_handle in person.get_parent_family_handle_list():
                            family = self.database.get_family_from_handle(family_handle)

                            create_spouse_relation(person, family)

                        fid, mid = create_parent_relation(person)
                        if fid:   # Father Gramps-ID
                            self.create_person_map('group', fid)
                        if mid:   # Mother Gramps-ID
                            self.create_person_map('group', mid)

                if person.family_list:
                    # iterate through this person's families
                    for family_handle in person.get_family_handle_list():
                        family = self.database.get_family_from_handle(family_handle)

                        create_spouse_relation(person, family)
                        recursive = False if self.config['number']['followparents'] else True
                        create_children_relation(family, recursive)

                if person.person_ref_list:
                    create_reference_relation(person)
        return

    def __create_gender(self, person_gender, spouse=False):
        """
        Creates a Gender based on the person_gender.
        """
        gender = Person.UNKNOWN
        if spouse:
            if person_gender == 'M': gender = Person.FEMALE
            elif person_gender == 'F': gender = Person.MALE
        else:
            if person_gender == 'M': gender = Person.MALE
            elif person_gender == 'F': gender = Person.FEMALE

        return gender

    def _create_or_update_person(self, source, pid, gen, \
                                name='', gender='U', spouse=False, \
                                bdate=None, bplace=None, ddate=None, dplace=None):
        """ creates a Person based on the name. """

        # nid = 'IND-%s:%s' % (pid, gender)
        # if nid in self.person_dict:
        if name in self.person_dict and gen == self.person_dict[name]['gen']:
            person = self.database.get_person_from_handle(self.person_dict[pid]['handle'])
            # return 'old', person

        else: # create a new Person
            person = Person()

            gramps_id = self.database.find_next_person_gramps_id()
            person.set_gramps_id(gramps_id)
            handle = create_id()
            person.set_handle(handle)

            person_name = self.__create_name(name)
            if person_name: person.set_primary_name(person_name)

            person_gender = self.__create_gender(gender, spouse)
            person.set_gender(person_gender)

        nid = 'IND-' + pid
        person_attr = create_attribute(source + nid, AttributeType.ID)
        if person_attr: person.add_attribute(person_attr)

        person_attr = create_attribute(str(gen), AttributeType.CUSTOM, "Generation")
        if person_attr: person.add_attribute(person_attr)

        if bdate or bplace:
            birth_date, __, __, __ = create_date_from_text(bdate)
            birth_place = self.__get_or_create_place(bplace)
            __, birth_ref = self.__create_event_and_ref(EventType.BIRTH, date=birth_date, place=birth_place)
            if birth_ref: person.set_birth_ref(birth_ref)

        if ddate or dplace:
            death_date, __, __, __ = create_date_from_text(ddate)
            death_place = self.__get_or_create_place(dplace)
            __, death_ref = self.__create_event_and_ref(EventType.DEATH, date=death_date, place=death_place)
            if death_ref: person.set_death_ref(death_ref)

        return 'new', person

    def create_person(self):
        """ Perform the generation of Person's """
        self.analyze.append('Processing %s file ...' % self.csv_import['import_file_IND'])

        data = open_file(self.csv_import['import_file_IND'], 'csv')
        if not data: return None

        pid, fid = 0, 0
        person_start, person_anzahl = 0 +7, self._DataAmount_   #  7: Leerzeilen
        person_end = len(data)

        with DbTxn(_("Person creation"), self.database, batch=True) as self.trans:
            row_number = person_start
            while row_number < person_end:
                if row_number > person_start + person_anzahl +1: break

                rowM = data[row_number]
                if rowM and rowM[0][0] == '#': continue   # comment lines starts with '#'

                if rowM[0] in ['IV.44']:
                    a = 1

                person, spouse = None, None
                genM = roman.fromRoman(rowM[0].split('.')[0])   # converting roman generation number to integer
                if rowM[2] != '' and rowM[2] != '[privacy]':   # Person
                    __, person = self._create_or_update_person(source='IND-', pid=rowM[0], gen=genM, \
                                                        name=rowM[2], gender=rowM[1], \
                                                        bdate=rowM[4], bplace=rowM[3], ddate=rowM[9], dplace=rowM[8])
                    if not _DEBUG_:
                        self.database.commit_person(person, self.trans)   # add & commit ...
                        if not rowM[2] in self.person_dict:
                            self.person_dict[rowM[2]] = {'nid': rowM[0], 'gen': genM, 'handle': person.handle}

                        pid += 1
                        print('%4i. Ind: %s: %s [%s]' % (pid, rowM[0], rowM[2], person.gramps_id))
                        self.analyze.append('%4i. Ind: %s: %s [%s]' % (pid, rowM[0], rowM[2], person.gramps_id))

                if rowM[7] != '':   # Spouse
                    rowF = data[row_number +1]
                    genF = roman.fromRoman(rowF[0].split('.')[0])
                    if rowF and rowF[0][0] == '#': continue   # comment lines starts with '#'

                    if rowM[2] == rowF[7] and rowF[7] == rowM[2]:   #  kreuzweiser vergleich
                        if rowF[2] != '[privacy]':   # ausnutzen der paarweisen Gleichheit, aber keine Spouse Zuweisung!
                            spouse_nid, spouse_name = rowF[0], rowF[2]
                            __, spouse = self._create_or_update_person(source='IND-', nid=spouse_nid, gen=genF, \
                                                            name=spouse_name, gender=rowF[1], \
                                                            bdate=rowF[4], bplace=rowF[3], ddate=rowF[9], dplace=rowF[8])
                        row_number += 1
                    elif rowM[7] != '[privacy]':
                        spouse_nid, spouse_name = rowM[0], rowM[7]
                        __, spouse = self._create_or_update_person(source='IND-', nid=spouse_nid, gen=genM, \
                                                                  name=spouse_name, gender=rowM[1], spouse=True)
                    if not _DEBUG_:
                        if spouse:
                            self.database.commit_person(spouse, self.trans)   # add & commit ...
                            if not spouse_name in self.person_dict:
                                spouse_gen = roman.fromRoman(spouse_nid.split('.')[0])
                                self.person_dict[spouse_name] = {'nid': spouse_nid, 'gen': spouse_gen, \
                                                                 'handle': spouse.handle}

                            pid += 1
                            print('%4i. Ind: %s: %s [%s]' % (pid, rowM[0], rowM[7], spouse.gramps_id))
                            self.analyze.append('%4i. Ind: %s: %s [%s]' % (pid, rowM[0], rowM[7], spouse.gramps_id))

                row_number += 1

                if rowM[7] == '' or rowF[7] == '':
                    continue   # No mariagge! if blank

                if person or spouse:
                    generation = roman.fromRoman(rowM[0].split('.')[0])   # converting roman generation number to integer
                    person_name = rowM[2].split(',')[0] if person else 'N.N.'
                    spouse_name = rowF[2].split(',')[0] if spouse else 'N.N.'
                    mdate, mplace = rowM[6].strip(), rowM[5].strip()
                    __, family, __ = self.__find_or_create_family('IND-', rowM[0], generation, \
                                                                  person_name, spouse_name, mdate, mplace)

                    if person:
                        family.set_father_handle(person.handle)
                        person.add_family_handle(family.get_handle())

                    if spouse:
                        family.set_mother_handle(spouse.handle)
                        spouse.add_family_handle(family.get_handle())

                    if not _DEBUG_:   # add & commit ...
                        if person: self.database.commit_person(person, self.trans)
                        if spouse: self.database.commit_person(spouse, self.trans)
                        self.database.commit_family(family, self.trans)

                        fid += 1
                        print('%4i. Fam: %s: %s -- %s [%s]' % \
                              (fid, rowM[0], person_name, spouse_name, family.gramps_id))
                        self.analyze.append('%4i. Fam: %s: %s -- %s [%s]' % \
                                            (fid, rowM[0], person_name, spouse_name, family.gramps_id))

        self.analyze.stop()

        self.database.enable_signals()
        self.database.request_rebuild()

        return None

    def complete_person(self):
        """ Perform the completion of Persons. """

        _debug_ = False

        # self.analyze = AnalyzeFile(self.config['name']['analyze'])
        # self.analyze.start()

        self.event = CompleteEvent(self.database, self.substitute)

        person_dict = {}
        person_start, person_stop = 0, 9999
        person_handle_list = list(self.database.iter_person_handles())

        for person_idx, person_handle in enumerate(person_handle_list[person_start:], start=person_start):
            if person_idx > person_start + person_stop: break
            person = self.database.get_person_from_handle(person_handle)
            if person is None: continue

            # Name
            ord_name = ordName(person)
            ord_name.print_name(person_idx, person.gramps_id, ord_name.Basename)

            # Citation
            citation = person.get_citation_list()[0] \
               if person.get_citation_list() else []

            # Events
            for event_ref in person.get_event_ref_list():
                if not event_ref.ref: continue
                event = self.database.get_event_from_handle(event_ref.ref)
                if not event: continue

                # Citation, Place, Occupation Event
                self.event.complete_event(event, citation)

                # Christen Event
                if self.event.complete_event_christen(person, event):
                    a = 1

            # Sortierung: Event Referenz
            event_ref_list = self.event.sort_event_ref(person)
            person.set_event_ref_list(event_ref_list)
            person_dict[person_idx] = [person]

        self.database.disable_signals ()
        if not _debug_ and len(person_dict) > 0:
            with DbTxn(_("Person completion"), self.database, batch=True) as trans:
                for key, value in person_dict.items():   # 0: Person
                    self.database.commit_person(value[0], trans)
        # self.analyze.stop()

        self.database.enable_signals()
        self.database.request_rebuild()

    # ============================================================================================================================ #
    def _apply_numbers(self, person_id):
        """"""
        def _apply_lists(person, numbering_local=True):
            """"""
            person_id = person.get_gramps_id()[1:]
            if person_id in self.person_dict:
                if self.config['number']['protect'] and \
                   self.config['number']['begin-id'] <= person.gramps_id <= self.config['number']['end-id']:
                    self.source_set.remove(person_id)
                    return

                self.target_id += 1
                target_id = self.target_id
                if self.target_mode in ['C', 'T']:  # C-ontinuous
                    if numbering_local:
                        if self.target_id % 2 == 0:   # target_id even!
                            if person.gender == Person.FEMALE: target_id += 1
                        else:   # target_id odd!
                            if person.gender != Person.FEMALE: target_id += 1
                elif self.target_mode == 'S':   # S-ingle
                    for act_id in range(self.start_id, self.target_id +2):
                        if act_id not in self.target_list:
                            if act_id % 2 == 0:   # = act_id even!
                                if person.gender == Person.MALE:
                                    target_id = act_id
                                    break
                            else:   # act_id odd!
                                if person.gender != Person.MALE:
                                    target_id = act_id
                                    break

                    success = False
                    for t in range(self.start_id, target_id):
                        success = True if t in self.target_list else False
                    if success: self.start_id = act_id

                if self.target_mode != 'C':  # C-ontinuous
                    if not target_id in self.target_list:
                        self.target_list.append(target_id)
                    else: exit(1)   # Error!

                if target_id > self.target_id:
                    self.target_id = target_id
                target_str = 'I' + str(target_id).zfill(5)
                if not target_id in self.target_dict:
                    self.target_dict[target_id] = self.person_dict[person_id]
                    self.target_dict[target_id]['tid'] = target_str
                    self.source_set.remove(person_id)
                else: exit(1)   # Error!

                # ToDo: Altnummer als Attribut eintragen

                if person.gender == Person.FEMALE and target_id % 2 == 0:   # target_id even!
                    self.statistik['fnFemale'] += 1
                if person.gender == Person.MALE and target_id % 2 != 0:   # target_id odd!
                    self.statistik['fnMale'] += 1

                self.analyze.append('%3d %48s: %s -> %s' % \
                    (len(self.target_dict), self.target_dict[target_id]['name'], \
                     self.target_dict[target_id]['pid'], self.target_dict[target_id]['tid']))
            return

        def _apply_spouse(spouse):
            """"""
            if spouse.get_gramps_id()[1:] in self.source_set:
                _apply_lists(spouse)

            for spouseparents_handle in spouse.get_parent_family_handle_list():
                spouseparents = self.database.get_family_from_handle(spouseparents_handle)
                if spouseparents:
                    spousefather_handle = spouseparents.get_father_handle()
                    if spousefather_handle:
                        spousefather = self.database.get_person_from_handle(spousefather_handle)
                        if spousefather.get_gramps_id()[1:] in self.source_set:
                            _apply_lists(spousefather)

                    spousemother_handle = spouseparents.get_mother_handle()
                    if spousemother_handle:
                        spousemother = self.database.get_person_from_handle(spousemother_handle)
                        if spousemother.get_gramps_id()[1:] in self.source_set:
                            _apply_lists(spousemother)

        # -------------------------------------------------------------------- #
        person_handle = self.person_dict[person_id]['handle']
        if person_handle:
            person = self.database.get_person_from_handle(person_handle)
            if person.gramps_id[1:] in self.source_set:
                _apply_lists(person)

        if person.family_list:
            # iterate through this person's families
            for family_handle in person.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)

                # include the spouse from this person's family
                spouse_handle = utils.find_spouse(person, family)
                if spouse_handle:
                    if self.target_mode == 'S':
                        self.target_mode = 'T'   # T-emporay switch of Target Mode
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    _apply_spouse(spouse)

                for child_ref in family.get_child_ref_list():
                    child = self.database.get_person_from_handle(child_ref.ref)
                    if child.gramps_id[1:] in self.source_set:
                        if child.get_family_handle_list():
                            child_id = child.get_gramps_id()[1:]
                            self._apply_numbers(child_id)
                        else:
                            _apply_lists(child, False)
        return

    def complete_person_number(self):
        """"""
        _debug_ = False

        print("Renumbering Person ID's ...")
        self.create_person_map \
            (self.config['number']['mode'], self.config['number']['person-id'])

        self.analyze = AnalyzeFile(self.config['number']['analyze'])
        self.analyze.start()

        source_id = self.config['number']['person-id'][1:]
        self.source_set = set(self.person_dict.keys())

        self.target_mode = 'C'  # C-ontinuous
        self.target_id = int(self.config['number']['start-id'][1:]) -1
        self.target_list = []
        self._apply_numbers(source_id)

        self.start_id = self.target_id +1
        while len(self.source_set) > 0:
            self.target_mode = 'S'  # S-ingle
            self.target_id = max(self.target_dict)
            for source_id in self.source_set:
                break

            self._apply_numbers(source_id)

        self.target_count = self.target_id - int(self.config['number']['start-id'][1:])
        cnt_str = 'Zähler Personen: %5d\n' % self.target_id
        anz_str = 'Anzahl Personen: %5d\n' % len(self.target_dict)
        den_str = 'Personendichte : %3.1f%%\n' % (len(self.target_dict) / self.target_count *100)
        falsenumber_str = 'Falsche Nummer Anz.  Male/Female: %4d / %4d\n' % (self.statistik['fnMale'], self.statistik['fnFemale'])
        falsequote_str = 'Falsche Nummer Quot. Male/Female: %3.1f%% / %3.1f%%\n' % \
            ((self.statistik['fnMale'] / len(self.target_dict) *100), (self.statistik['fnFemale'] / len(self.target_dict) *100))
        print(cnt_str, anz_str, den_str, falsenumber_str, falsequote_str)

        self.database.disable_signals()
        if not _debug_ and len(self.target_dict) > 0:
            with DbTxn(_("Person Gramps-Id sorting"), self.database, batch=True) as trans:
                for key, value in self.target_dict.items():   # 0: Person
                    person = self.database.get_person_from_handle(value['handle'])
                    person.gramps_id = value['tid']
                    self.database.commit_person(person, trans)   # add & commit ...

        self.analyze.append('\n')
        self.analyze.append(cnt_str)
        self.analyze.append(anz_str)
        self.analyze.append(den_str)
        self.analyze.append(falsenumber_str)
        self.analyze.append(falsequote_str)
        self.analyze.stop()

        self.database.enable_signals()
        self.database.request_rebuild()

        return

    def complete_person_groupname(self):
        """"""
        _debug_ = True
        person_dict = {}

        def complete_groupname(person, personname, nametype):
            """"""
            success = False
            person_altnames = person.get_alternate_names()
            for altname in person_altnames:
                if altname.get_type().value == nametype:
                    altname.group_as = personname.groupname
                    person_dict[person.gramps_id]['altnames'] = person_altnames
                    success = True
            return success

        print("Complete Person's Groupname ...")

        self.analyze = AnalyzeFile(self.config['name']['analyze'])
        self.analyze.start()

        person_dict = create_person_map(self.database)

        for i, pid in enumerate(person_dict):
            person = self.database.get_person_from_gramps_id(pid)
            person_name = ordName(person, groupas=True)

            if person_name and person_name.groupname:
                """
                complete_groupname(person, person_name, NameType.MARRIED)
                if success:
                    self.analyze.append('%s:: [%s] Pers: %s!%s §%s§-> %s!%s' % \
                        (i, pid, person_name.groupname, person_name.lastname, person_name.marriagename, \
                         person_name.groupname, person_name.marriagename))
                """
                success = complete_groupname(person, person_name, NameType.AKA)
                if success:
                    self.analyze.append('%s:: [%s] Pers: %s!%s §%s§-> %s!%s' % \
                        (i, pid, person_name.groupname, person_name.lastname, person_dict[person.gramps_id]['altnames'], \
                         person_name.groupname, person_dict[person.gramps_id]['altnames']))
                a = 1
        self.analyze.stop()

        self.database.disable_signals()
        if len(self.person_dict) > 0:
            with DbTxn(_("Person's Groupname completion"), self.database, batch=True) as trans:
                for key, value in self.person_dict.items():   # 0: Person
                    person = self.database.get_person_from_handle(value['handle'])
                    person.alternate_names = value['altnames']
                    if not _debug_:
                        self.database.commit_person(person, trans)   # add & commit ...

        self.database.enable_signals()
        self.database.request_rebuild()

        return
