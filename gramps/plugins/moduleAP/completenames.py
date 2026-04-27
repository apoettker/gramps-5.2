# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2022   Alois Poettker
#

"""Tools/Database Processing Name Completion"""

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import roman

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

from gramps.gen.db import DbTxn
from gramps.gen.lib import (Name, NameType, Surname)

from gramps.plugins.libAP.libbase import *
from gramps.plugins.libAP.libnameobject import _PREFIXES_ as _PREFIXES_
from gramps.plugins.libAP.libnameobject import _SUFFIXES_ as _SUFFIXES_

# Leerzeichen wichtig!
_CONJUNCTIONS_ = [' auch ',  ' dictu ', ' en ', ' oder ', ' sive ', ' später ', ' und ']
_SPECIALCHAR_ = ['"', '„', '“']

# --------------------------------------------------------------------------
class CompletePersonName():

    def __init__(self, database, substitute, config):
        """"""
        self.database = database
        self.substitute = substitute
        self.config = config

        self.substname_prim, self.substname_sec, self.substname_thrd = False, False, False

    def erase_name(self, name_one, name_two):
        # substitute primary name out of substitute name
        return name_one.replace(name_two, '').replace('  ', ' ').strip()

    def create_name_lists(self, database):
         # look for existing person's, build a map
        print('Building Name Lists ...')

        firstmalenames_list, firstfemalenames_list, surname_list = [], [], []

        cursor = self.database.get_person_cursor()
        data = next(cursor)
        i = 1   # Debug!
        while data:
            (handle, val) = data

            for i in [3, 4]:
                if val[i]:
                    if i == 3 and val[3][4]:
                        firstnames = [firstname for firstname in val[3][4].split(' ') \
                                      if not (firstname in firstmalenames_list) and \
                                         not (firstname in firstfemalenames_list) and \
                                         not ('.' in firstname)]
                        if firstnames:
                            if val[2] == 0: firstfemalenames_list.extend(firstnames)
                            elif val[2] == 1: firstmalenames_list.extend(firstnames)
                    else:
                        for key, value4 in enumerate(val[4]):
                            firstnames = [firstname for firstname in value4[4].split(' ') \
                                          if not (firstname in firstmalenames_list) and \
                                             not (firstname in firstfemalenames_list) and \
                                             not ('.' in firstname)]
                            if firstnames:
                                if val[2] == 0: firstfemalenames_list.extend(firstnames)
                                elif val[2] == 1: firstfemalenames_list.extend(firstnames)

                    if i == 3 and val[3][5]:
                        # if val[3][5][0]: prefix = val[3][5][0][1]
                        if val[3][5][0] and not (val[3][5][0][0] in surname_list):
                            surname_list.append(val[3][5][0][0])
                    else:
                        for key, value4 in enumerate(val[4]):
                            if value4[5][0] and not (value4[5][0][0] in surname_list):
                                surname_list.append(value4[5][0][0])

            data = next(cursor)
            i += 1
        cursor.close()
        firstmalenames_sort = sorted(list(filter(None, firstmalenames_list)))
        firstfemalenames_sort = sorted(list(filter(None, firstfemalenames_list)))
        surname_sort = sorted(list(filter(None, surname_list)))

        return firstmalenames_sort, firstfemalenames_sort, surname_sort

    def modify_firstnames(self, Name, action, element, original, substitute):
        """"""
        firstnames = ''
        for item in Name.get_first_name().split():
            if action == 'erase' and \
               substitute == item:
                continue
            elif action == 'replace' and \
               original == item:
                item = item.replace(original, substitute)
            firstnames += '%s ' % item
        Name.set_first_name(firstnames.strip())

    def modify_surname_list(self, Name, action, element='', original='', substitute=''):
        """"""
        for item in list(Name.get_surname_list()):
            Name.remove_surname(item)
            if action == 'add':
                if element == 'p':   #  Prefix
                    item.prefix = substitute
            elif action == 'capitalize':
                item.surname = item.surname.title()   # Capitalize item
            elif action == 'erase':
                item.surname = self.erase_name(item.surname, substitute)
            elif action == 'replace':
                if element == 'p':   #  Prefix
                    item.prefix = substitute
                elif element == 'S' and \
                     original.lower() in item.surname.lower():   #  Surname
                    item.surname = ' '.join(substitute) if type(substitute) is list else substitute
            Name.add_surname(item)

    # ============================================================================================================================ #
    def split_prefix(self, ordname, primname):
        # process Prefix splitting

        lastname_split = ordname.lastname.split()
        for prefix in _PREFIXES_:
            if prefix in lastname_split:
                ordname.prefix = prefix.strip()
                ordname.lastname = self.erase_name(ordname.lastname, prefix)
                ordname.surname = self.erase_name(ordname.surname, prefix)
                ordname.set_composename(None, None, None, prefix=prefix)

                self.modify_surname_list(primname, 'add', 'p', ordname.prefix, lastname_split[0].strip())
                self.modify_surname_list(primname, 'replace', 'S', ordname.lastname, lastname_split[1:])
                break

    def substitute_prefix(self, ordname, primname, substname):
        # process Prefix substitute
        action_prefix, orig_prefix, subst_prefix, __ = \
            self.substitute.compare_person('prefix', ordname.prefix)
        if action_prefix:
            self.substname_prim |= action_prefix == 'create'
            if action_prefix == 'replace':
                self.modify_surname_list(primname, 'replace', 'p', orig_prefix, subst_prefix)
                self.modify_surname_list(substname, 'replace', 'p', orig_prefix, subst_prefix)
        return

    def split_suffix(self, ordname, primname, substname):
        # process Suffix splitting
        firstname_split = ordname.firstnames.replace('.', '').upper().split()
        lastname_split = ordname.lastname.replace('.', '').upper().split()
        for suffix in _SUFFIXES_:
            if suffix in firstname_split:
                # Delete suffix form SUFFIXES list out of primary firstname
                ordname.firstnames = self.erase_name(ordname.firstnames, suffix + '.')
                ordname.firstnames = self.erase_name(ordname.firstnames, suffix)

                suffix += '.' if '.' not  in suffix else ''
                ordname.set_composename(None, None, suffix=suffix.strip())

                primname.set_first_name(ordname.firstnames)
                primname.set_suffix(suffix)
                substname.set_first_name(ordname.firstnames)
                substname.set_suffix(suffix)
                break

            if suffix in lastname_split:
                ordname.lastname = self.erase_name(ordname.lastname, suffix)
                ordname.surname = self.erase_name(ordname.surname, suffix)

                suffix += '.' if '.' not  in suffix else ''
                ordname.set_composename(None, None, suffix=suffix.strip())

                primname.set_suffix(suffix)
        substname.set_suffix(suffix)

        suffix_as_digit = [s for s in list(ordname.firstnames) if s.isdigit()]
        if suffix_as_digit:
            suffix = roman.toRoman(int(suffix_as_digit[0])) + '.'
            ordname.firstnames = self.erase_name(ordname.firstnames, suffix_as_digit[0])

            primname.set_suffix(suffix)
            self.modify_firstnames(primname, 'erase', 'F',  ordname.firstnames, suffix_as_digit[0])
            substname.set_suffix(suffix)
            self.modify_firstnames(substname, 'erase', 'F',  ordname.firstnames, suffix_as_digit[0])

        return

    def substitute_suffix(self, ordname, primname, substname):
        # process Suffix Substitution
        action_suffix, orig_suffix, subst_suffix, __ = \
            self.substitute.compare_person('suffix', ordname.suffix)
        if action_suffix:
            self.substname_prim |= action_suffix == 'create'
            if action_suffix == 'replace':
                primname.set_suffix(subst_suffix)
                substname.set_suffix(subst_suffix)
        return

    def substitute_firstnames(self, person, ordname, primname, substname):
        # process Firstname Substitution
        if not ordname.firstnames:
            primname.set_first_name('N.N.')
            substname.set_first_name('N.N.')

        action_firstname, orig_firstnames, subst_firstnames, subst_firstadd = \
            self.substitute.compare_person('firstname', ordname.firstnames, \
                                           gender=person.gender)
        if action_firstname:
            self.substname_prim |= action_firstname == 'create'
            if action_firstname == 'create':
                substname.set_first_name(subst_firstnames)
                if subst_firstadd:
                    self.modify_firstnames(primname, 'replace', 'F', subst_firstadd[0], subst_firstadd)
                primname.set_type((NameType.CUSTOM, CALL_NAMETYPE))
            elif action_firstname == 'replace':
                ordname.firstnames = subst_firstnames
                primname.set_first_name(subst_firstnames)

                if orig_firstnames == '(?)':
                    if self.firstnames_note and self.firstnames_note.handle:
                        person.add_note(self.firstnames_note.handle)
            elif action_firstname == 'dubnick':
                ordname.firstnames = self.erase_name(ordname.firstnames, subst_firstnames)
                primname.set_first_name(subst_firstnames)
                primname.set_nick_name(orig_firstnames)
            elif action_firstname == 'shiftP':
                ordname.firstnames = self.erase_name(ordname.firstnames, subst_firstadd)
                prim_transname = self.erase_name(primname.get_firstname(), subst_firstadd)
                prim_transname = prim_transname.replace('(', '').replace(')', '').strip()
                primname.set_first_name(prim_transname)
                subst_transname = self.erase_name(substname.get_firstname(), subst_firstadd)
                subst_transname = subst_transname.replace('(', '').replace(')', '').strip()
                substname.set_first_name(subst_transname)

                ordname.suffix = subst_firstnames
                primname.set_suffix(subst_firstnames)
                substname.set_suffix(subst_firstnames)
        return

    def substitute_translationname(self, person, ordname, primname, substname):
        # process Translationname Substitution
        action_transname, orig_transnames, subst_transnames, __ = \
            self.substitute.compare_person('translation', ordname.firstnames, \
                                           gender=person.gender)
        if action_transname:
            self.substname_prim |= action_transname in ['create', 'delete']

            # Delete translation name out of primary first / second names
            if (orig_transnames in primname.firstname) and \
               (subst_transnames in primname.firstname):
                prim_transname = self.erase_name(primname.get_firstname(), orig_transnames)
                prim_transname = prim_transname.replace('(', '').replace(')', '').strip()
                primname.set_first_name(prim_transname)

                subst_transname = self.erase_name(substname.get_firstname(), subst_transnames)
                subst_transname = subst_transname.replace('(', '').replace(')', '').strip()
                substname.set_first_name(subst_transname)
            else:
                self.modify_firstnames(primname, 'replace', 'F', orig_transnames, subst_transnames)

            if action_transname == 'call':
                ordname.callname = subst_transnames
                primname.set_callname(subst_transnames)
            elif action_transname in ['create', 'explain']:
                self.substname_sec |= action_transname == 'explain'
                # Create new altername name and make it primary later
                # Explain new altername name
                ordname.firstnames = subst_transnames
                # Delete primary original firstname out of substitute name
                if subst_transname: substname.set_first_name(subst_transname)
                else: substname.set_first_name(subst_transnames)
            elif action_transname == 'delete':
                # Delete translation name out of substitute first names
                ordname.firstnames = primname.get_firstname()

            if action_transname in ['create', 'delete']:
                # Delete call names if exist
                if ordname.callname in subst_transnames:
                    primname.set_callname('')
                    substname.set_callname('')
        return

    def substitute_alternativename(self, person, ordname, primname, substname, thirdname):
    # process Alternativename Substitution
        action_altname, orig_akanames, subst_akanames, __ = \
            self.substitute.compare_person('akaname', ordname.firstnames, \
                                           gender=person.gender)
        if action_altname:
            if action_altname == 'explain':
                self.substname_prim |= True
                # ordname.firstnames = self.erasename(ordname.firstnames, subst_akanames)
                ordname.firstnames = subst_akanames
                primname.set_first_name(ordname.firstnames)
                """
                if len(ordname.firstnames.split(' ')) > 1:
                    tmpname = self.erasename(substname.firstname, orig_akanames)
                else: tmpname = subst_akanames
                substname.set_first_name(tmpname)
                """
                substname.set_first_name(orig_akanames)
                substname.set_type(AKA_NAMETYPE)

            elif action_altname == 'shiftL':
                substname_prim, substname_sec, substname_thrd = True, True, True

                ordname.firstnames = self.erase_name(ordname.firstnames, subst_akanames)
                # Delete translation name out of primary first / second names
                prim_transname = self.erase_name(primname.get_firstname(), subst_akanames)
                primname.set_first_name(prim_transname)
                subst_transname = self.erase_name(substname.get_firstname(), subst_akanames)
                substname.set_first_name(subst_transname)

                thirdname = Name(source=substname)   # Additional Nametype
                thirdname.set_type((NameType.CUSTOM, AKA_NAMETYPE))
                thirdname.set_surname_list([Surname()])
                thirdname.surname_list[0] = subst_akanames

            elif action_altname == 'switch':
                if len(ordname.firstnames.split(' ')) > 1:
                    substname_sec |= True
                    ordname.firstnames = self.erase_name(ordname.firstnames, orig_akanames)
                    primname.set_first_name(ordname.firstnames)
                    substname.set_type(AKA_NAMETYPE)
                    tmpname = self.erase_name(substname.firstname, subst_akanames)
                    substname.set_first_name(tmpname)

        return

    def substitute_callname(self, person, ordname, primname, substname):
        # process Callname Substitution ('(' in Family-Tree)
        if '(' in ordname.firstnames:
            ordname.callname = ordname.firstnames.split('(', 1)[1].split(')', 1)[0]
            primname.set_call_name(ordname.callname)

            # Delete "()" out of first names
            temp_firstnames = self.erase_name(substname.get_first_name(), '(')
            subst_firstnames = self.erase_name(temp_firstnames, ')')
            primname.set_first_name(subst_firstnames)

            if self.substname_prim:
                substname.set_callname(ordname.callname)
                substname.set_first_name(subst_firstnames)

        # process Callname Substitution ('"' in GES-2000)
        if '"' in ordname.firstnames:
            ordname.callname = ordname.firstnames.split('"', 1)[1].split('"', 1)[0]
            primname.set_callname(ordname.callname)

            # Delete "" out of first names
            subst_firstnames = self.erase_name(substname.get_first_name(), '"')
            primname.set_first_name(subst_firstnames)

            if self.substname_prim:
                substname.set_call_name(ordname.callname)
                substname.set_first_name(subst_firstnames)

        # process Callname Substitution ('„“' in Ancestry)
        if '„' in ordname.firstnames:
            ordname.callname = ordname.firstnames.split('„', 1)[1].split('“', 1)[0]
            primname.set_call_name(ordname.callname)

            # Delete „“ out of first names
            # subst_firstnames = ''.join(c for c in ordname.firstnames if c not in _SPECIALCHAR_)
            complete_callname = '„%s“' % ordname.callname
            subst_firstnames = self.erase_name(substname.get_first_name(), complete_callname)
            primname.set_first_name(subst_firstnames)

            if self.substname_prim:
                substname.set_call_name(ordname.callname)
                substname.set_first_name(subst_firstnames)
        return

    def add_nickname(self, person, ordname, primname, substname):
        # process Nickname Addition
        act_nickname, orig_nickname, subst_nickname, __ = \
            self.substitute.compare_person('nickname', ordname.firstnames, \
                                           gender=person.gender)
        if act_nickname:
            self.substname_prim |= act_nickname == 'create'

            if act_nickname == 'expand':
                nomen = ordname.firstnames.split(orig_nickname)[1].split(' ')[0]
                orig_nickname += nomen
                subst_nickname += ' %s' % nomen

            #  Set nick name(s)
            if act_nickname == 'explain':
                self.substname_sec |= True
                primname.set_nick_name(orig_nickname)
            elif act_nickname in ['expand','replace']:
                primname.set_nick_name(subst_nickname)

            substname.set_nick_name(subst_nickname)

            # Delete nick name out primary first names
            ordname.firstnames = self.erase_name(ordname.firstnames, orig_nickname)
            ordname.set_composename()
            primname.set_first_name(ordname.firstnames)

            # Delete nick name out substitute first names
            subst_firstnames = self.erase_name(substname.get_first_name(), orig_nickname)
            substname.set_first_name(subst_firstnames)
        return

    def add_groupname(self, person, ordname, primname, substname):
        # process Groupname Addition
        act_groupname, orig_group, subst_group, subst_groupname = \
            self.substitute.compare_person('groupname', ordname.lastname, \
                                           gender=person.gender)
        if act_groupname:
            self.substname_prim |= act_groupname == 'replace'

            primname.set_group_as(subst_group)
            substname.set_group_as(subst_group)
            if act_groupname == 'replace':
                self.modify_surname_list(primname, 'erase', 'S', ordname.lastname, orig_group)
                self.modify_surname_list(substname, 'erase', 'S', ordname.lastname, orig_group)
        return

    def process_callname(self, person, ordname, primname, substname):
        # process Call name
        if ordname.callname in _SUFFIXES_:
            ordname.callname = ''
        if not ordname.callname:
            # Call name out of nickname
            nickname = ordname.nickname
            if nickname and nickname in ordname.firstnames:
                primname.set_nick_name('')
                primname.set_call_name(nickname)
                substname.set_nick_name('')
                substname.set_call_name(nickname)
            else:
            # Call name out of firstnames
                number = 0   # Firstname number
                firstnames = ordname.firstnames.split(' ')
                if len(firstnames) > 1:   # Two or more firstnames
                    if self.config['name']['callname_estimation']:
                        firstnames_length = [i for i, x in enumerate(firstnames) if len(x) > 2]
                        # firstname_pos = next(i for i in firstnames_length if i)
                        if firstnames_length:   # No abreviated Firstname
                            date_options = {'endnote': False, 'year_only': True}
                            birth_year, __ = determine_birthdate(self.database, person, date_options)
                            if birth_year:
                                # No abreviated Firstname, Birth year in Callname Years!
                                if (len(firstnames[1]) > 2 and firstnames[1][1] != '.') and \
                                    (CALLNAME_YEAR_LOW < birth_year < CALLNAME_YEAR_HIGH):
                                    number = 1

                            if substname.first_name:
                                callname = substname.first_name.split(' ')
                                substname.set_call_name(callname[number])
                    primname.set_call_name(firstnames[number])
        return

    def substitute_lastname(self, person, ordname, primname, substname):
        # process Lastname Substitution
        action_lastname, orig_lastname, subst_lastname, __ = \
            self.substitute.compare_person('lastname', ordname.lastname)
        if action_lastname:
            self.substname_prim |= action_lastname == 'create'
            if action_lastname == 'delete':
                self.substname_sec |= True
                self.modify_surname_list(primname, 'erase', 'S', ordname.lastname, subst_lastname)
                self.modify_surname_list(substname, 'erase', 'S', ordname.lastname, orig_lastname)
            elif action_lastname == 'group':
                primname.set_group_as(subst_lastname)
                substname.set_group_as(subst_lastname)
            elif action_lastname == 'replace':
                # substname_sec |= True
                self.modify_surname_list(primname, 'replace', 'S', orig_lastname, subst_lastname)
                self.modify_surname_list(substname, 'replace', 'S', orig_lastname, subst_lastname)
                if orig_lastname == '?':
                    if self.surnames_note and self.surnames_note.handle:
                        person.add_note(self.surnames_note.handle)
        return

    def split_lastname(self, person, ordname, primname, substname):
        # process Lastname Splitting
        for conjunction in _CONJUNCTIONS_:
            if conjunction in ordname.lastname:
                name_split = ordname.lastname.split()

                surname = Surname()
                surname.primary = False
                surname.prefix = name_split[1].strip()
                surname.surname = name_split[2].strip()

                self.modify_surname_list(primname, 'replace', 'S', ordname.lastname, name_split[0].strip())
                primname.add_surname(surname)
                if self.substname_sec:
                    self.modify_surname_list(substname, 'replace', 'S', ordname.lastname, name_split[2].strip())
                    substname.add_surname(surname)

                self.substitute_prefix(primname, substname, name_split[1].strip())
        return

    def process_nametype(self, person, primname):
        # process Name Types
        # primname_val = primname.get_type().value
        primname_str = primname.get_type().string
        date_options = {'endnote': False, 'year_only': True}
        birth_year, __ = determine_birthdate(self.database, person, date_options)
        death_year, __ = determine_deathdate(self.database, person, date_options)
        if primname.get_first_name() == "N.N." and primname.get_surname() == "N.N.":
            primname.set_type(NameType.UNKNOWN)
        elif birth_year and birth_year < CIVIL_REGISTRY_YEAR:   # 2: Birth_NameType
            primname.set_type((NameType.CUSTOM, BAPT_NAMETYPE))
        elif death_year and death_year < CIVIL_REGISTRY_YEAR:
            primname.set_type((NameType.CUSTOM, BAPT_NAMETYPE))
        elif keys_true(self.config, 'name', 'nametype_enforcement'):
            primname.set_type((NameType.CUSTOM, self.config['name']['nametype_enforcement']))

        altnames_change = False
        altnames_list = person.get_alternate_names()
        for nr, altname in enumerate(altnames_list):
            altname_val = altname.get_type().value
            # altname_str = altname.get_type().string
            if birth_year and altname_val == 2 and birth_year < CIVIL_REGISTRY_YEAR:   # 2: Birth_NameType
                altname.set_type((NameType.CUSTOM, CALL_NAMETYPE))
                altnames_change = True

            primname_str = primname.get_type().string
            altname_str = altnames_list[nr].get_type().string
            # check for double Name Types
            if primname_str == altname_str:
                print('  Doppelter Typ: %s' % altname_str)
                pass
        if altnames_change:
            person.set_alternate_names(altnames_list)

        return

    # ============================================================================================================================ #
    def complete_person_name(self):
        """
        Perform the completion of Person Names.
        """
        _debug_ = False

        self.analyze = AnalyzeFile(self.config['name']['analyze'])
        self.analyze.start()

        self.firstnames_note = create_note('Vorname(n) nicht gesichert.', NoteType.PERSONNAME)
        self.surnames_note = create_note('Nachname(n) nicht gesichert.', NoteType.FAMILY)

        with DbTxn(_("Note creation"), self.database, batch=True) as trans:
            if not _debug_:
                self.database.add_note(self.firstnames_note, trans)
                self.database.add_note(self.surnames_note, trans)

        person_list = []
        person_start, person_anzahl = 0, 9999
        person_handle_list = list(self.database.iter_person_handles())
        for person_idx, person_handle in enumerate(person_handle_list[person_start:], start = person_start):
            if person_idx > person_start + person_anzahl -1: break
            person = self.database.get_person_from_handle(person_handle)
            if person is None: continue
            # date_options = {'endnote': False, 'year_only': True}
            # birth_year, __ = determine_birthdate(self.database, person, date_options)

            # Debug
            if person_idx == 2093:
                a = 1
            if person.gramps_id == 'I00026':
                a = 1

            # Name(s)
            self.substname_prim, self.substname_sec, self.substname_thrd = False, False, False

            ord_name = ordName(person)
            prim_name = ord_name.Basename
            # self.modify_surname_list(prim_name, 'capitalize')
            subst_name = Name(source=prim_name)   # Additional Nametype
            # self.modify_surname_list(subst_name, 'capitalize')
            subst_name.set_type((NameType.CUSTOM, SUBST_NAMETYPE))
            third_name = None

            # process Prefix splitting
            self.split_prefix(ord_name, prim_name)

            # process Suffix splitting
            self.split_suffix(ord_name, prim_name, subst_name)

            # process Firstname Substitution
            self.substitute_firstnames(person, ord_name, prim_name, subst_name)

            # process Translationname Substitution
            self.substitute_translationname(person, ord_name, prim_name, subst_name)

            # process Alternativename Substitution
            self.substitute_alternativename(person, ord_name, prim_name, subst_name, third_name)

            # process Callname Substitution
            self.substitute_callname(person, ord_name, prim_name, subst_name)

            # process Nickname Addition
            self.add_nickname(person, ord_name, prim_name, subst_name)

            # process Groupname Addition
            self.add_groupname(person, ord_name, prim_name, subst_name)

            # process Call name
            self.process_callname(person, ord_name, prim_name, subst_name)

            # process Prefix Substitution
            self.substitute_prefix(ord_name, prim_name, subst_name)

            # process Suffix Substitution
            self.substitute_suffix(ord_name, prim_name, subst_name)

            # process Lastname Substitution
            self.substitute_lastname(person, ord_name, prim_name, subst_name)

            # process Lastname Splitting
            self.split_lastname(person, ord_name, prim_name, subst_name)

            # process Name Types
            self.process_nametype(person, prim_name)

            # set Name in Person
            if self.substname_prim:
                person.set_primary_name(subst_name)
                person.add_alternate_name(prim_name)
            else:
                person.set_primary_name(prim_name)
            if self.substname_sec:
                person.add_alternate_name(subst_name)
            if self.substname_thrd:
                person.add_alternate_name(third_name)

            if self.analyze.enable:
                if self.substname_prim:
                    line = ord_name.print_name(person_idx, person.gramps_id, prim_name, '>', subst_name)
                elif self.substname_sec:
                    line = ord_name.print_name(person_idx, person.gramps_id, prim_name, '+', subst_name)
                else:
                    line = ord_name.print_name(person_idx, person.gramps_id, prim_name)
                if line: self.analyze.append(line)

            person_list.append(person)

        self.database.disable_signals()
        if not _debug_ and person_list:
            with DbTxn(_("Name completion"), self.database, batch=True) as trans:
                for person in person_list:
                    self.database.commit_person(person, trans)

        self.analyze.stop()

        self.database.enable_signals()
        self.database.request_rebuild()

        return True
