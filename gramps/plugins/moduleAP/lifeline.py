"""Reports/Text Reports/LifeLine Report"""

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
from gramps.gen.proxy import CacheProxyDb

from gramps.plugins.libAP.libbase import *

class LifeLineReport:
    """LifeLine Report """

    def __init__(self, database, options):
        self.database = CacheProxyDb(database)
        self.options = options

        self.pid = options.base['pid']
        self.gen_keys = options.gen_keys
        self.index_map = options.index_map
        self.handle_map = options.handle_map

    def write(self, report):
        # write Lifeline report´
        path_name, report_text = \
            apply_filehead(report, self.database, self.pid, self.options.base['result_path'], 'LifeLine', 'Lfe', 'tex')
        lifeline_file = open(path_name, mode='w', buffering=1)
        lifeline_file.writelines('%% %s' % report_text)

        lifeline_tmp, lifeline_list = [], []
        act_generation = 1
        new_generation = True
        if report == 'A':
            for key in sorted(self.handle_map):
                if key >= 2**act_generation:
                    act_generation += 1
                    new_generation = True
                    lifeline_tmp.append('\\midrule\n')
                    lifeline_tmp.extend(lifeline_list)
                    lifeline_list = lifeline_tmp.copy()
                    lifeline_tmp.clear()

                person_handle = self.handle_map[key]
                person = self.database.get_person_from_handle(person_handle)

                # Lifeline
                options = {'mode': 1, 'new_generation': new_generation, 'act_generation': act_generation,
                           'rindent': False, 'groupname': self.options.include['person']['groupnames'], 'index_map': self.index_map}
                life_line = apply_lifeline(self.database, person, options)
                if life_line:
                    lifeline_tmp.append(life_line)

                new_generation = False

            for line in lifeline_list: # reversed(lifeline_list):
                lifeline_file.writelines(line)

        if report == 'D':
            for act_generation in range(len(self.gen_keys)):
                new_generation = True
                lifeline_file.writelines('\\midrule\n')
                for key in self.gen_keys[act_generation]:

                    person_handle = self.handle_map[key]
                    person = self.database.get_person_from_handle(person_handle)
                    if not self.options.include['common']['private'] and person.private:
                        continue

                    # Lifeline
                    options = {'mode':2, 'new_generation': new_generation, 'act_generation': act_generation,
                               'rindent': False, 'groupname': self.options.include['person']['groupnames'], 'index_map': self.index_map}
                    life_line = apply_lifeline(self.database, person, options)
                    if life_line: lifeline_file.writelines(life_line)

                    new_generation = False

        # Lifeline
        lifeline_file.writelines('\n')
        lifeline_file.close()

        return True

    def apply_YManc_list(self, handle):
        """"""
        if not handle: return

        person = self.database.get_person_from_handle(handle)
        gender = 'M' if person.gender else 'F'

        act_generation = 1
        for __ in range (1, 99):    # person changes in the loop
            desc_family_handle = person.get_main_parents_family_handle()
            if desc_family_handle:
                person = None
                act_generation += 1
                family = self.database.get_family_from_handle(desc_family_handle)
                if gender == 'M':   #  Male
                    father_handle = family.get_father_handle()
                    if father_handle:
                        person = self.database.get_person_from_handle(father_handle)
                if gender == 'F':   #  Female
                    mother_handle = family.get_mother_handle()
                    if mother_handle:
                        person = self.database.get_person_from_handle(mother_handle)

                options = {'mode':1, 'new_generation': True, 'act_generation': act_generation,
                           'rindent': False, 'groupname': self.options.include['person']['groupnames'], 'index_map': self.index_map}
                ymline = apply_lifeline(self.database, person, options)
                if ymline: self.YMline_list.append(ymline)
            else:
                break
        self.YMline_list.reverse()

        return True

    def apply_YMdesc_line(self, handle_neu, gender_orig, cur_gen=0):
        """"""
        #  max_gen +1 wg. genealogischer Nummer
        if (not handle_neu) or (cur_gen > self.options.base['max_generation']):
            return

        person = self.database.get_person_from_handle(handle_neu)
        gender = 'M' if person.gender else 'F'
        if gender == gender_orig:
            options = {'mode':2, 'new_generation': True, 'act_generation': cur_gen,
                       'rindent': False, 'groupname': self.options.include['person']['groupnames'], 'index_map': self.index_map}

            ymline = apply_lifeline(self.database, person, options)
            if ymline: self.YMline_list.append(ymline)
            if cur_gen == 0: self.YMline_list.append('\\midrule\n')

            for family_handle in person.get_family_handle_list():
                family = self.database.get_family_from_handle(family_handle)
                for child_ref in family.get_child_ref_list():
                    if child_ref.ref:
                        self.apply_YMdesc_line(child_ref.ref, gender_orig, cur_gen +1)

        return True

    def write_YM(self, report):
        """
        Y: patrilineare Vererbung (Y-Chromosom)
        M: matrilineare Vererbung (mitochondriale DNA)
        """
        path_name, report_text = \
            apply_filehead(report, self.database, self.pid, self.options.base['result_path'], 'YM-Linie', 'YM_Lne', 'tex')
        ymline_file = open(path_name, mode='w', buffering=1)
        ymline_file.writelines('%% %s' % report_text)

        self.YMline_list = []

        person = self.database.get_person_from_gramps_id(self.pid)
        options = {'mode':1, 'new_generation': True, 'act_generation': 1,
                   'rindent': False, 'groupname': self.options.include['person']['groupnames'], 'index_map': self.index_map}
        ymline = apply_lifeline(self.database, person, options)
        if ymline: self.YMline_list.append(ymline)

        if report == 'A':
            self.apply_YManc_list(person.handle)
        if report == 'D':
            gender = 'M' if person.gender else 'F'
            self.apply_YMdesc_line(person.handle, gender)

        for line in self.YMline_list:
            ymline_file.writelines(line)
        ymline_file.writelines('\n\n')
        ymline_file.close()

        return True

