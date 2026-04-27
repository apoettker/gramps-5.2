#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2012  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2013-2014  Paul Franklin
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

"""Reports/Text Reports/End of Line Report"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.errors import ReportError
from gramps.gen.proxy import CacheProxyDb

from gramps.plugins.libAP.libbase import *

#------------------------------------------------------------------------
#
# EndOfLineReport
#
#------------------------------------------------------------------------
class EndOfLineReport:
    """ EndOfLine Report """

    def __init__(self, database, options, user):
        """
        Create the EndOfLineReport object that produces the report.

        The arguments are:

        database        - the Gramps database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.
        name_format   - Preferred format to display names
        incl_private  - Whether to include private data
        living_people - How to handle living people
        years_past_death - Consider as living this many years after death
        """
        self.database = CacheProxyDb(database)
        self.base = options.base

        self.center_person = self.database.get_person_from_gramps_id(self.base['pid'])
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % self.base['pid'])

        # eol_map is a map whose:
        #   keys are the generations of the people
        #   values are a map whose:
        #      keys are person handles
        #      values are an array whose:
        #         elements are an array of ancestor person handles that link
        #         the eol person handle to the person or interest
        # eol_map[generation][person_handle][pedigree_idx][ancestor_handle_idx]
        #
        # There is an array of pedigrees because one person could show up twice
        # in one generation (descendants marrying). Most people only have one
        # pedigree.
        #
        # eol_map is populated by get_eol() which calls itself recursively.
        self.eol_map = {}
        self.get_eol(self.center_person, 1, [])

    def get_eol(self, person, gen, pedigree):
        """
        Recursively find the end of the line for each person
        """
        person_handle = person.get_handle()
        new_pedigree = list(pedigree) + [person_handle]
        person_is_eol = False
        families = person.get_parent_family_handle_list()

        if person_handle in pedigree:
            # This is a severe error!
            # It indicates a loop in ancestry: A -> B -> A
            person_is_eol = True
        elif not families:
            person_is_eol = True
        else:
            for family_handle in families:
                family = self.database.get_family_from_handle(family_handle)
                father_handle = family.get_father_handle()
                mother_handle = family.get_mother_handle()
                if father_handle:
                    father = self.database.get_person_from_handle(father_handle)
                    self.get_eol(father, gen+1, new_pedigree)
                if mother_handle:
                    mother = self.database.get_person_from_handle(mother_handle)
                    self.get_eol(mother, gen+1, new_pedigree)

                if not father_handle or not mother_handle:
                    person_is_eol = True

        if person_is_eol:
            # This person is the end of a line
            if gen not in self.eol_map:
                self.eol_map[gen] = {}
            if person_handle not in self.eol_map[gen]:
                self.eol_map[gen][person_handle] = []
            self.eol_map[gen][person_handle].append(new_pedigree)

    def write_endofline(self, report):
        """
        The routine that actually creates the report.
        """
        path_name, report_text = \
            apply_filehead(report, self.database, self.base['pid'], self.base['result_path'], 'Spitzenahnen', 'Spitz', 'tex')
        eol_file = open(path_name, mode='w', buffering=1)
        eol_file.writelines('%% %s' % report_text)

        self.text_list = []
        for generation, handles in sorted(self.eol_map.items()):
            self.text_list.append("\\listHead{Generation %d}{xx Personen}\n" % (generation -1))

            number = 1
            for person_handle, pedigrees in handles.items():
                valid = self.write_person_row(person_handle, number)
                if valid:
                    self.write_pedigree_row(pedigrees[0])
                    number += 1

            self.text_list.append("\\listTail\n\n")

        for text_line in self.text_list:
            if text_line: eol_file.write(text_line)

        # Closing
        eol_file.writelines('\n')
        eol_file.close()

        return True

    def write_person_row(self, person_handle, number):
        """
        Write the head with information about the given person.
        """
        person = self.database.get_person_from_handle(person_handle)
        ord_name = ordName(person)   # Extract the right names
        if not ord_name.valid: return False
        if ord_name.lastname == 'N.N.': return False

        options = {'endnote': False, 'year_only': True}
        byear, __ = determine_birthdate(self.database, person, options)
        byear = byear if byear else ''
        dyear, __ = determine_deathdate(self.database, person, options)
        dyear = dyear if dyear else ''

        if number == 1:
            self.text_list.append("\\tableLabel(0ex){%i}\n" % number)
        else:
            self.text_list.append("\\tableLabel{%i}\n" % number)
        line = ord_name.linename
        if byear or dyear: line += '[(%s -- %s)]' % (byear, dyear)
        self.text_list.append("\\tableItem%s" % line)

        return True

    def write_pedigree_row(self, pedigree):
        """
        Write a row with with the person's family line.
        pedigree is an array containing the names of the people in the pedigree
        """
        if not pedigree: return

        path = list(reversed(pedigree))
        lineage = get_lineage(self.database, path, prefix='<-s>', suffix= '<s>')
        self.text_list.append("%s\n" % lineage)
