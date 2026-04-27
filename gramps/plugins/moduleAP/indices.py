"""Reports/Text Reports/Indices Report"""

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
from gramps.gen.lib import Person

from gramps.plugins.libAP.libbase import *

class IndexReport:
    """Index Report """

    def __init__(self, database, options):
        self.database = CacheProxyDb(database)
        self.options = options

        self.pid = options.base['pid']
        self.gen_keys = options.gen_keys
        self.index_map = options.index_map
        self.handle_map = options.handle_map

        self.list_base = ListBase()
        self.family_base = FamilyBase(database)

        self.center_person = database.get_person_from_gramps_id(self.pid)
        if (self.center_person == None) :
            raise ReportError(_("Person %s is not in database") % self.pid)

    # Index methods
    def get_ind_index(self, person, ext=False, prefix='', attribute=None):
        """"""
        person_handle = person.get_handle()
        gen_str = get_gen_str(self.index_map, self.report, person_handle)

        ord_name = ordName(person, groupas=self.options.include['person']['groupnames'])   # Extract the right names
        ind_index = '\\%sInd[%s]%s ' % (prefix, gen_str, ord_name.linename)
        # ind_index = self.apply_ind_index(prefix, gen_str, '', \
        #    ord_name.firstnames, '', ord_name.prefix, ord_name.surname, person.gramps_id, attribute)

        location_list = []
        """
        __,  __, locations, __ = self.apply_person_narr('i', prefix, person)   # i: Index mode
        if locations:
            for location in locations:
                if attribute: location += '[%s]' % attribute
                location_list.append(location)
        """
        return ind_index, location_list

    def get_fam_index(self, person, ext=True, prefix='', attribute=None):
        """"""
        fam_index, location_list = '', []
        for family_handle in person.get_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)
            family_prefix, father_shortname, mother_shortname = self.family_base.apply_head(family)
            if not (father_shortname or mother_shortname):
                continue

            if fam_index: fam_index += '\n  '
            if ext:
                if person.get_gender() == Person.MALE:
                    spouse_handle = family.get_mother_handle()
                else:
                    spouse_handle = family.get_father_handle()
                if spouse_handle:
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    spouse_index, __ = self.get_ind_index(spouse, prefix='i')
                    fam_index += '%s\n  ' % spouse_index
                """
                for child_ref in family.get_child_ref_list():
                    child_handle = child_ref.ref
                    child = self.database.get_person_from_handle(child_handle)

                    child_index, __ = self.get_ind_index(child)
                    fam_index += '%s\n  ' % child_index
                """
            fam_index += '\\%sFam' % prefix
            if family_prefix:
                fam_index += '[%s!%s]' % (family_prefix[0], family_prefix[1])
            fam_index += '{%s}{%s}[%s]' % (father_shortname, mother_shortname, family.gramps_id)
            """
            __, __, __, __, locations, __ = self.apply_marriage_narr(prefix, person)
            if locations:
                for location in locations:
                    if attribute:
                        location = location.replace('iLoc', 'mLoc')
                        location += '[%s]' % attribute
                    location_list.append(location)
            """
        return fam_index, location_list

    def write_if_index(self, idx_file, key):
        """Individuals, Families"""

        person_handle = self.handle_map[key]
        person = self.database.get_person_from_handle(person_handle)

        # self.narrator.set_subject(person)

        indent = '  ' if key > 1 else ''
        ind_index, __ = self.get_ind_index(person, prefix='i')
        fam_index, __ = self.get_fam_index(person, prefix='i')
        idx_file.writelines(indent)
        if ind_index: idx_file.writelines(ind_index)
        if fam_index: idx_file.writelines(fam_index)
        idx_file.writelines('\n')

        return True

    def write_ifl_index(self, idx_file, key, location_list):
        """Individuals, Families, Locations"""

        person_handle = self.handle_map[key]
        person = self.database.get_person_from_handle(person_handle)

        # self.narrator.set_subject(person)
        indent = '  ' if key > 1 else ''
        ind_index, locations = self.get_ind_index(person, True, 'i')
        if ind_index: idx_file.writelines('%s%s\n' % (indent, ind_index))
        if locations: location_list.extend(locations)

        fam_index, locations = self.get_fam_index(person, False, 'i')
        if fam_index: idx_file.writelines('%s%s\n' % (indent, fam_index))
        if locations: location_list.extend(locations)

        loc_index = self.list_base.apply(location_list, '', 'see', 'C', 'S', ' ')   # Compress, Sort
        if loc_index:
            idx_file.writelines('%s%s\n' % (indent, loc_index))
            del location_list[:]

        return True

    def write_index(self, report):
        """"""
        self.report = report
        path_name, index_text = \
            apply_filehead(report, self.database, self.pid, self.options.base['result_path'], 'Indizes', 'Idx', 'tex')
        idx_file = open(path_name, mode='w', buffering=1)
        idx_file.writelines('%% %s' % index_text)

        if report == 'D':
            path_name, extindex_text = \
                apply_filehead(report, self.database, self.pid, self.options.base['result_path'], 'Extended Indizes', 'Ext', 'tex')
            ext_file = open(path_name, mode='w', buffering=1)
            ext_file.writelines('%% %s' % extindex_text)

        act_generation = 1
        location_list = []
        start_str, end_str = '\n\\isInRange', '{'
        gender_str = 'Male' if self.center_person.gender else 'Female'

        if report == 'A':
            for key in sorted(self.handle_map):
                if key >= 2**act_generation:
                    if act_generation > 1:
                        idx_file.writelines('}{}\n')
                    if act_generation > 0:
                        idx_file.writelines('\n%% %s %%' % ('-'*75))
                        low_line = r'{\lowVorfahr%s}' % gender_str
                        high_line = r'{\highVorfahr%s}' % gender_str
                        line = '%s%s{%s}%s%s' % \
                            (start_str, low_line, act_generation, high_line, end_str)

                        idx_file.writelines('%s\n' % line)
                    act_generation += 1

                self.write_ifl_index(idx_file, key, location_list)

        if report == 'D':
            for act_generation in range(len(self.gen_keys)):
                if act_generation > 1:
                    idx_file.writelines('}{}\n')
                    ext_file.writelines('}{}\n')
                if act_generation > 0:
                    low_line = r'{\lowVorfahr%s}' % gender_str
                    high_line = r'{\highVorfahr%s}' % gender_str
                    line = '%s%s{%s}%s%s' % \
                        (start_str, low_line, act_generation, high_line, end_str)
                    idx_file.writelines('%s\n' % line)
                    ext_file.writelines('%s\n' % line)

                for key in self.gen_keys[act_generation]:
                    self.write_ifl_index(idx_file, key, location_list)
                    self.write_if_index(ext_file, key)

        # file closing
        idx_file.writelines('}{}\n\n')
        idx_file.writelines('%% %s %%\n' % ('-'*75))
        idx_file.writelines('\\endinput\n\n')
        idx_file.close()

        if report == 'D':
            ext_file.writelines('}{}\n\n')
            ext_file.writelines('%% %s %%\n' % ('-'*75))
            ext_file.writelines('\\endinput\n\n')
            ext_file.close()

        return
