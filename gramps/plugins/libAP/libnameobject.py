# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020  Alois Poettker
#

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import copy

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.lib import NameType
from gramps.gen.display.name import displayer as global_name_display

# Spaces necessary to avoid false positive!
_PREFIXES_ = ["auf dem", "von der", "von dem", "vor dem", "vam den", "van der", \
                 "d'", "de", "della", "geb.", "gen.", "gnt.", "im", "in", "of", \
                 "ten", "ter", "van", "von", "vom", "zum", "zur", "zu"]
_spPREFIXES_ = [" auf dem", " von der", " von dem", " vor dem", " vam den", " van der", \
                 " d'", " de", " geb.", " gen.", " gnt.", " im", " in", " of", \
                 " ten", " ter", " van", " von", " vom", " zum", " zur", " zu"]
_SUFFIXES_ = ['VIII', 'VII', 'VI', 'V', 'IV', 'III', 'II', 'I', 'JR', 'SR']
_spSUFFIXES_ = [' VIII', ' VII', ' VI', ' V', ' IV', ' III', ' II', ' I', ' JR', ' SR']
_NN_ = ['\\\\NN', 'N. N.', 'N N', 'NN.', 'N.N.', 'N.N', 'NN', 'N ']

class ordName(object):
    """ Class to extract the right names out of Gramps """

    def __init__(self, person, name=None, nametype=None, groupas=False):
        """"""
        self.clear()
        self.group_as = groupas

        # Copy the global NameDisplay so that we don't change application defaults
        if person:
            self._name_display = copy.deepcopy(global_name_display)
            __, __, __, __, __ = self.get_ordinary_name(person, name, nametype, groupas)
            pass

    def __repr__(self):
        return '%s' % self.linename

    def __str__(self):
        return '%s' % self.linename

    # Name methods
    def print_name(self, base_idx, base_id, base_name, action=None, alt_name=None):
        """"""
        line = 'Ind %s: [%s] ' % (base_idx, base_id)

        prefix = ' '.join(base_name.get_prefixes())
        surname = ''
        surname_list = base_name.get_surnames()
        for i, item in enumerate(surname_list):
            surname += '%s ' % item
        surname = surname.strip()
        if not surname:
            print("Fehler ")

        if base_name.title: line += 'T:%s ' % base_name.get_title()
        if prefix: line += 'p:%s ' % prefix
        line += 'L:%s' % surname
        if base_name.group_as: line += '=G:%s' % base_name.get_group_as()
        line += ', F:%s' % base_name.first_name.strip()
        if base_name.call: line += " C:(%s)" % base_name.get_call_name()
        if base_name.suffix: line += ' s:%s' % base_name.get_suffix()
        if base_name.nick: line += ", N:'%s'" % base_name.get_nick_name()

        if action:
            line += ' %s ' % action

            prefix = alt_name.get_prefixes()
            surname = ''
            surname_list = alt_name.get_surnames()
            for i, item in enumerate(surname_list):
                surname += '%s ' % item
            surname = surname.strip()

            if alt_name.title: line += 'T:%s ' % alt_name.get_title()
            if prefix: line += 'p:%s ' % prefix
            line += 'L:%s' % surname
            if alt_name.group_as: line += '=G:%s' % alt_name.get_group_as()
            line += ', F:%s' % alt_name.first_name.strip()
            if alt_name.call: line += ' C:(%s)' % alt_name.get_call_name()
            if alt_name.suffix: line += ' s:%s' % alt_name.get_suffix()
            if alt_name.nick: line += ', N:%s' % alt_name.get_nick_name()

        print(line)

        return line

    def get_firstnames(self, Name):
        """"""
        if not Name: return ''

        firstnames = ''
        for name in Name:
            # name_type = name.get_type().value   # Debug
            name_string = name.get_type().string
            if name_string in ['Geburtsname', 'Rufname', 'Taufname']:   # 2, 0, 0 (0: Custom Name)
                if len(name.get_first_name().splitlines()) != 1:   # bug 9242
                    firstnames = "".join(name.get_first_name().splitlines())
                else:
                    firstnames = name.get_first_name()
                    suffix = name.get_suffix()
                    if suffix: firstnames += ' %s' % suffix

        return firstnames

    def get_birthname(self, Name):
        """"""
        if not Name: return ''

        surnames = ''
        for name in Name:
            sname = name.get_surname_list()
            for snme in sname:
                name_type = name.get_type().value
                if name_type == 2:   # 2: Birth Name
                    pre = snme.get_prefix()
                    if pre: surnames += '%s ' % pre
                    surnames += snme.get_surname()

        return surnames.strip()

    def get_nametype(self, nametype):
        """"""
        string = nametype.string   # type.values not always equal on all platforms!

        if string == 'Auch bekannt als': symbol = '\\ntA'   # Also known as
        elif string == 'Geburtsname': symbol = '\\ntG'   # Birth name
        elif string == 'Taufname': symbol = '\\ntB'   # Baptised name
        elif string == 'Name nach der Hochzeit': symbol = '\\ntM'   # Married name
        elif string == 'Rufname': symbol = '\\ntR'   # Call name
        elif string == 'Transkription': symbol = '\\ntT'   # Transcripted name
        elif string == 'Unbekannt': symbol = '\\ntU'   # Unknown name
        else: symbol = ""

        return symbol

    def get_alternate_name(self, altnames, nametype):
        """"""
        for altname in altnames:
            if altname.get_type().value == nametype:
                return altname.get_primary_surname()

        return False

    def get_citationname(self):
        """"""
        # Geburtsname wg. Transkription oft in 'Alternatenames'
        firstnames = self.get_firstnames(self.Altnames)
        if not firstnames:
            firstnames = self.firstnames
            if self.suffix:
                if not '.' in self.suffix:
                    self.suffix += '.'
                firstnames += ' %s' % self.suffix

        surname = self.get_birthname(self.Altnames)
        if not surname:
            surname = self.surname

        return firstnames, surname

    def __modify_name(self, Name, original, substitute):
        """"""
        Name.first_name = Name.get_first_name().replace(original, substitute)
        first_name = 'n.' if 'n.' in Name.first_name.lower() else ''

        surname_list = Name.get_surname_list()
        for element in surname_list:
            Name.remove_surname(element)
            sur_name = element.surname.lower()
            if original.lower() in sur_name:
                element.surname = substitute
            if first_name and ('n' == sur_name or 'n.' in sur_name):
                Name.first_name = Name.get_first_name().replace('N.', '').strip()
                if Name.first_name == '': Name.first_name = '\\NN'
                element.surname = '\\NN'
            Name.add_surname(element)

    def normalize_name(self, Name, norm):
        """"""
        Name.first_name = Name.get_first_name()
        if any(item == Name.first_name.upper() for item in _NN_):
            Name.first_name = norm

        surname_list = Name.get_surname_list()
        for element in surname_list:
            if any(item == element.surname.upper() for item in _NN_):
                element.surname = norm

    def get_ordinary_name(self, person, source=None, name=None, nametype=None, groupas=False):
        """
        Defines person's given name and short name
        """
        self.Basename = source if source else person.get_primary_name()
        if len(self.Basename.surname_list) > 1 and not self.Basename.surname_list[0].primary:
            self.Basename.surname_list.sort(key = lambda x: x.primary, reverse=True)
        self.Altnames = person.get_alternate_names()
        if self.Altnames:
            for altname in self.Altnames:
                if len(altname.surname_list) > 1 and not altname.surname_list[0].primary:
                    altname.surname_list.sort(key = lambda x: x.primary, reverse=True)
        self.normalize_name(self.Basename, '\\NN')
        for altname in self.Altnames:
            if altname: self.normalize_name(altname, '\\NN')

        self.nametype = self.get_nametype(self.Basename.get_type())
        self.title = self.Basename.get_title()   #  The title
        self.firstnames = self.Basename.get_first_name()   # All first names
        self.callname = self.Basename.get_call_name()   # Only the callname
        self.nickname = self.Basename.get_nick_name()   # Only the nickname
        self.suffix = self.Basename.get_suffix() # The first name suffix

        self.groupname = self.Basename.group_as
        prim_surname = self.Basename.get_primary_surname()   # The primary Surname objective
        self.prefix = prim_surname.prefix.strip()   # The last name prefix
        self.lastname = prim_surname.surname.strip()   # The last name
        self.surname = self.Basename.get_surname()   # The prefix & last name

        """ Old Style
        prim_surname = ''
        if self.prefix: prim_surname += '%s ' % self.prefix
        prim_surname += '%s' % self.Basename.get_surname()
        for prefix in self._PREFIXES_:
            if prefix in prim_surname:
                lastname = prim_surname.split(prefix, 1)
                self.lastname = lastname[1].strip() if lastname[1] else lastname[0].strip()
                self.prefix = prefix.strip() # The last name prefix
                break
        """
        firststring = ''
        firstcount = len (self.firstnames.split(' '))   # Amount of firstnames(s)
        callflag = 0   # Callname is: -1: nickname, 0: No, 1: callname, 2: one of the firstnames(s)
        if not name:
            name = self._name_display.display_formal(person)
        namestr = name.replace(',', '')

        self.givenname = self.firstnames.split(' ', 1)[0] # The initial givename

        for iter in namestr.split(' '):
            if iter in self.firstnames:   # Check the firstnames(s)
                if firstcount > 1:   # Two or more firstnames's
                    if (not self.callname and callflag == 0) or \
                       (iter == self.callname):
                        firststring += '(%s) ' % iter
                        self.givenname = iter   # Givenname defined by part of firstnames
                        callflag = 2   # Callnameflag is this part of Firstnames
                        continue
                firststring += '%s ' % iter

            # if iter in self.lastname:   # Process the lastname(s)
            if self.callname and callflag == 0:   # Callname in quotes behind the firstnames(s)
                self.givenname = self.callname   # Givenname defined by callname
                callflag = 1   # Callnameflag is Callname

        # Short Names
        self.shortname = self.givenname
        if self.prefix: self.shortname += ' %s' % self.prefix
        self.shortname += ' %s' % self.lastname
        if self.suffix: self.shortname += ' %s' % self.suffix
        self.valid = self.shortname != '\\NN \\NN'

        # Brief Name
        self.briefname = '%s\n%s' % (self.givenname,  self.surname)  # surname: prefix + lastname
        if self.suffix: self.briefname += ' %s' % self.suffix

        # Marriage Name
        self.marriagename = ''
        marriagename = self.get_alternate_name(self.Altnames, NameType.MARRIED)
        if marriagename:
            #  if self.firstnames: self.marriagename += '%s ' % self.firstnames
            if marriagename.prefix: self.marriagename += '%s ' % marriagename.prefix
            self.marriagename += marriagename.surname

        # Full Name
        self.fullname = ''
        if self.firstnames: self.fullname += self.firstnames
        if self.surname:
            if self.fullname: self.fullname += ' '
            self.fullname += self.surname

        # Line-Name (TeX optimized)
        for item in _NN_:
            if firststring == '\\NN': continue
            if item in firststring: firststring = firststring.replace(item, '\\NN')
        # firststring = firststring.replace('\\NN', '\\NN')
        for item in _NN_:
            if self.lastname == '\\NN': continue
            if item in self.lastname: self.lastname  = self.lastname.replace(item, '\\NN')
        # self.lastname = self.lastname.replace('\\NN', '\\NN')
        self.set_linename(firststring, person.gramps_id)

        # Sort Name
        self.sortname = ''
        if self.prefix: self.sortname += '%s ' % self.prefix
        self.sortname += '%s' % self.lastname
        self.sortname += ', %s' % self.givenname if self.givenname in self.firstnames else self.firstnames
        if self.suffix: self.sortname += ' %s' % self.suffix

        return self.firstnames, self.prefix, self.lastname, \
               self.shortname, self.fullname

    def set_composename(self, givenname=None, firstnames=None, suffix=None, \
                        prefix=None, lastname=None, surname=None):
        """"""
        if prefix: self.prefix = prefix
        if suffix: self.suffix = suffix

        self.shortname = givenname if givenname else self.givenname
        if prefix: self.shortname += ' %s' % prefix
        elif self.prefix: self.shortname += ' %s' % self.prefix
        if lastname: self.shortname += ' %s' % lastname
        else: self.shortname += ' %s' % self.lastname
        if suffix: self.shortname += ' %s' % suffix
        elif self.suffix: self.shortname += ' %s' % self.suffix

        if firstnames: self.firstnames = firstnames
        if surname: self.surname = surname

        # Brief Name
        self.briefname = '%s\n' % givenname if givenname else '%s\n' % self.givenname
        if self.prefix: self.briefname += ' %s' % prefix if prefix else ' %s' % self.prefix
        self.briefname += ' %s' % lastname if lastname else ' %s' % self.lastname
        if self.suffix: self.briefname += ' %s' % suffix if suffix else ' %s' % self.suffix

        # Full Name
        self.fullname = ''
        if self.firstnames: self.fullname += '%s' % self.firstnames
        if self.surname:
            if prefix: self.fullname += ' %s' % prefix
            elif self.prefix: self.fullname += ' %s' % self.prefix
            self.fullname += ' %s' % self.surname
            if suffix: self.fullname += ' %s' % suffix
            elif self.suffix: self.fullname += ' %s' % self.suffix

        return None

    def set_linename(self, firstnames='', gramps_id='Ixxxxx'):
        """Compile Tex-Line name"""
        self.linename = ''
        if self.title: self.linename += '+%s+' % self.title
        self.linename += '{%s}' % firstnames.rstrip() \
            if firstnames else self.firstnames
        if self.callname and self.givenname != self.callname:
            self.linename += "'%s'" % self.callname
        elif self.nickname:
            self.linename += "'%s'" % self.nickname
        if self.prefix:
            self.linename += '+%s+' % self.prefix
        self.linename += '{%s!%s}' % (self.groupname, self.lastname) \
            if self.group_as and self.groupname else '{%s}' % self.lastname
        if self.suffix:
            self.linename += '+%s+' % self.suffix
        self.linename += '[%s]' % gramps_id

        return None

    def clear(self):
        """Clears all class variables"""
        self.Basename, self.Altnames = None, None

        self.valid = False
        self.callname, self.nickname, self.marriagename = '', '', ''
        self.givenname, self.firstnames = '', ''
        self.title = ''
        self.groupname = ''
        self.prefix, self.lastname, self.suffix = '', '', ''
        self_marriagename, self.surname = '', ''
        self.shortname, self.briefname, self.fullname = '', '', ''
        self.sortname = ''
        self.linename = '{\\NN}'   # TeX-Line name

# ============================================================================ #
class NameList(object):
    """"""
    def __init__(self, name_list):
        """ Class to administer / write name lists """
        if name_list:
            self.create(name_list)

    def create(self, name_list):
        """"""
        self.counter = 0
        self.debug = False
        # Items: Anzahl, Identifier, Name(n), Index, Zitat(e), Notiz(en)
        item = [0, 'None', [], [], [], []]   # Name element
        self.reg = []   # Name register!

        for name in name_list:
            new_element = copy.deepcopy (item)
            new_element[1] = name
            self.reg.append(new_element)
        pass

    def apply_citation(self):
        """ Apply citation to list """

        cit_list = []
        if self.counter > 0:
            for nr, __ in enumerate(self.reg):
                cit = self.reg[nr][4]
                if cit: cit_list += cit

        return cit_list

    def clear(self, name_list):
        """"""
        if not self.debug:
            del self.reg[:]
            self.create(name_list)
        self.debug = False
        self.counter = 0

# ============================================================================ #
