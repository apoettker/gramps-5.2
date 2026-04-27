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
import collections, copy
from collections import defaultdict

from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext
from gramps.gen.plug.report import utils as ReportUtils

from gramps.plugins.libAP.libbase import *

# Statistic Variable
gsMsumMB, gsMsumDB = 0, 1   # Male: 0: Sum. Marriage Age, 1: Sum. Death Age
gsFsumMB, gsFsumDB = 0, 1   # Female: 0: Sum. Marriage Age, 1: Sum. Death Age
gsCfrstMB, gsCavgMB, gsClstMB, gsCsumDB = 0, 1, 2, 3   # Child: 0/1/2: Sum. first/avg./last Marriage <-> Birth Age, 3: Sum. Death Age

def recursively_default_dict ():
    return collections.defaultdict(recursively_default_dict)

class GenBase(object):
    def __init__ (self):
        """
        Class for basic statistical data by generation
        """
        self.create()

    def create(self):
        """"""
        matrix_height, matrix_width = 20, 4   # 20 Generations, 4 Values
        # Triple: Quality, Count, Data
        # Male / Female: 0: Sum Marriage Age, 1: Avg. Death Age
        # Child: 0: Sum. First - Marriage, 2: Sum. Avg - Marriage, 3: Sum. Last - Marriage, 4: Death Age
        self.data = [[[0, 0, 0, 0] for x in range(matrix_width)] for y in range(matrix_height)]
        pass

    def clear(self):
        """"""
        del self.data [:]
        self.create ()

class GenStats(object):

    def __init__(self, data_list):
        """
        Class to administer / write statistical data by generation
        """

        if data_list:
            self.create(data_list)

    def create (self, data_list):
        """"""
        max_generation = 17
        # Male / Female: 0: Sum Marriage Age, 1: Avg. Death Age
        # Child: 0: Sum. First - Marriage, 2: Sum. Avg - Marriage, 3: Sum. Last - Marriage, 4: Death Age

        # 6x: quality, count, min, raw, max, interpol. data
        item = [[0, 0, 0, 0, 0, 0] for i in range(max_generation)]

        self.data = {}

        for name in data_list:
            element = copy.deepcopy(item)
            self.data[name] = element

        pass

class GenStat(object):
    """
    Class to administer / write statistical data by generation
    """
    def __init__ (self, database, datadict):
        """"""
        self.database = database
        self.datadict = datadict
        pass

    # Statistic methods
    def initialize_gen_stat(self):
        """"""
        self.datadict['rawMale'], self.datadict['rawFemale'] = 0, 0
        self.datadict['calcMale'], self.datadict['calcFemale'], self.datadict['calcChild'] = 0, 0, 0
        self.datadict['calcFamily'] = 0
        self.gen_person, self.gen_family = list(), list()

        for values in self.datadict['person_dict']:
            generation = values[1][0]
            person_handle = values[1][2]
            person = self.database.get_person_from_handle(person_handle)
            if person.gender == 0:
                self.datadict['rawFemale'] += 1
                continue   # Berechnet werden nur Männer!
            if person.gender == 1:
                self.datadict['rawMale'] += 1

            person_id, person_bdate, person_ddate = 'Ixxxx', 0, 0
            date_options = {'endnote': False, 'year_only': True}
            if person:
                self.datadict['calcMale'] += 1
                person_id = person.gramps_id
                person_bdate, __ = determine_birthdate(self.database, person, date_options)
                person_ddate, __ = determine_deathdate(self.database, person, date_options)
            self.gen_person.append([generation, 'M', person_id, person_bdate, person_ddate])

            for fmly_count, family_handle in enumerate(person.get_family_handle_list()):
                family = self.database.get_family_from_handle(family_handle)

                if family:
                    self.datadict['calcFamily'] += 1
                    family_id = family.gramps_id
                    family_mdate = self.find_marriage_date(family)

                spouse_id, spouse_bdate, spouse_ddate = 'Ixxxx', 0, 0
                child_count, child_sumage, child_firstage, child_lastage = 0, 0, 0, 0
                spouse_handle = ReportUtils.find_spouse(person, family)
                if spouse_handle:
                    spouse = self.database.get_person_from_handle(spouse_handle)
                    if spouse:
                        self.datadict['calcFemale'] += 1
                        spouse_id = spouse.gramps_id
                        spouse_bdate, __ = determine_birthdate(self.database, spouse, date_options)
                        spouse_ddate, __ = determine_deathdate(self.database, spouse, date_options)
                    self.gen_person.append([generation, 'F', spouse_id, spouse_bdate, spouse_ddate])

                    for child_ref in family.get_child_ref_list():
                        child_handle = child_ref.ref
                        child = self.database.get_person_from_handle(child_handle)

                        if child:
                            self.datadict['calcChild'] += 1
                            child_id = child.gramps_id
                            child_bdate, __ = determine_birthdate (self.database, child, date_options)
                            child_ddate, __ = determine_deathdate (self.database, child, date_options)
                            self.gen_person.append([generation, 'C', child_id, child_bdate, child_ddate])

                        if child_bdate > 0:
                            child_count += 1
                            # if childs bdate < mdate (eg. illegitimate childs): bdate = 1!
                            if child_count == 1: child_firstage = child_bdate - family_mdate
                            child_sumage += child_bdate - family_mdate # if child_bdate > family_mdate else 1
                            child_lastage = child_bdate - family_mdate

                if family_id:
                    gen_line = [generation, family_id, family_mdate,   # 00 -- 02
                                person_id, person_bdate, person_ddate,   # 03 -- 05
                                spouse_id, spouse_bdate, spouse_ddate,   # 06 -- 08
                                child_count, child_sumage, child_firstage, child_lastage]   # 09 -- 12
                    self.gen_family.append(gen_line)

    def norm_gen_stat(self, low, high, person, evt):
        """"""
        for gen in range(low, high):
            if person.data[gen][evt][2] == 0:
                if gen == low:
                    denom = person.data[1][evt][1] if person.data[1][evt][1] > 0 else 1
                    person.data[gen][evt][2] = person.data[1][evt][2] / denom
                elif gen > low and gen < high:
                    denom1 = person.data[gen][evt][1] if person.data[gen][evt][1] > 0 else 1
                    denom2 = person.data[gen +1][evt][1] if person.data[gen +1][evt][1] > 0 else 1
                    person.data[gen][evt][2] = (person.data[gen][evt][2] / denom1 +
                                                               person.data[gen +1][evt][2] / denom2) / 2.0
                elif gen == high:
                    denom = person.data[high][evt][1] if person.data[high][evt][1] > 0 else 1
                    person.data[gen][evt][2] = person.data[high][evt][2] / denom
                person.data[gen][evt][0], person.data[gen][evt][1] = 1, 1

        return person

    def apply_gen_stat(self, low, high, male, female, child):
        """Generation Statistic"""

        text_list = []
        text_list += '#  01;   02;  03;      04;   05;  06;      07;  08;  09;      10;  11;  12;      13;      14;     15;   16;      17;      18;      19\n'
        text_list += '# Gen;    Q;   C; MMrrAge;    Q;   C; MDthAge;   Q;   C; FMrrAge;   Q;   C; FDthAge;  MAbstd; FAbstd;    C;  CfBrth;  CAbstd;  ClBrth\n'
        for gen in range(low, high):
            text_list += '%5d;' % gen  # 01

            for evt in [gsMsumMB, gsMsumDB]:   # 0: Male Marriage <-> Birth, 1: Marriage <-> Death
                quality = male.data[gen][evt][1] / male.data[gen][evt][0] if male.data[gen][evt][0] > 0 else 0
                marriage = male.data[gen][evt][2] / male.data[gen][evt][1] if male.data[gen][evt][1] > 0 else 0
                text_list += '  %3.1f; %3d; %7.4f;' % (quality, male.data[gen][evt][1], marriage)   # 02 -- 07

            for evt in [gsFsumMB, gsFsumDB]:   # 0: Female Marriage <-> Birth, 1: Marriage <-> Death
                quality = female.data[gen][evt][1] / female.data[gen][evt][0] if female.data[gen][evt][0] > 0 else 0
                marriage = female.data[gen][evt][2] / female.data[gen][evt][1] if female.data[gen][evt][1] > 0 else 0
                text_list += ' %3.1f; %3d; %7.4f;' % (quality, female.data[gen][evt][1], marriage)   # 08 -- 13

            avgbirthage = child.data[gen][gsCavgMB][2] / child.data[gen][gsCavgMB][1] if child.data[gen][gsCavgMB][1] > 0 else 0

            avgmarriage = male.data[gen][0][2] / male.data[gen][0][1] if male.data[gen][0][1] > 0 else 0   # Male
            avgparentage = avgmarriage + avgbirthage if avgmarriage + avgbirthage > 0 else 0
            text_list += ' %7.4f;' % (avgparentage)   # 14

            avgmarriage = female.data[gen][0][2] / female.data[gen][0][1] if female.data[gen][0][1] > 0 else 0   # Female
            avgparentage = avgmarriage + avgbirthage if avgmarriage + avgbirthage > 0 else 0
            text_list += ' %7.4f;' % (avgparentage)   # 15

            text_list += ' %3d;' % child.data[gen][0][0]   # 16
            text_list += ' %7.4f; %7.4f; %7.4f' % (child.data[gen][gsCfrstMB][2], avgbirthage, child.data[gen][gsClstMB][2])   # 17 -- 19

            text_list += '\n'

        return text_list

    def analyse1_gen_stat(self, male, female, child):
        """"""
        text_list = []
        debug = True
        if debug:
            text_list += '#   1;   2;     3;     4;      5;     6;     7;      8;     9;    10;   11;   12\n'
            text_list += '# Gen; FNr;   FId; FMAge;    MId; MBAge; MDAge;    FId; FBAge; FDAge; CCnt; CSum\n'

        gen0 = 0
        for i, gen_family in enumerate(self.gen_family):
            gen = abs(gen_family[0])

            if debug:
                line = '#\n' if gen0 < gen else ''
                line += '# %3d; %3d; %5s; %5d;' % (gen_family[0], i +1, gen_family[1], gen_family[2])
                line += '%7s; %5d; %5d;' % (gen_family[3], gen_family[4], gen_family[5])
                line += '%7s; %5s; %5d;' % (gen_family[6], gen_family[7], gen_family[8])
                line += '%5d; %4d' % (gen_family[9], gen_family[10])
                text_list += '%s\n' % line

            male.data[gen][gsMsumMB][0] += 1   # Family Counter
            if gen_family[4] > 0 and gen_family[2] > 0:
                male.data[gen][gsMsumMB][1] += 1   # Marriage Counter
                male.data[gen][gsMsumMB][2] += gen_family[2] - gen_family[4]   # Sum. Marr. Age
            male.data[gen][gsMsumDB][0] += 1   # Family Counter
            if gen_family[4] > 0 and gen_family[5] > 0:
                male.data[gen][gsMsumDB][1] += 1   # Death Counter
                male.data[gen][gsMsumDB][2] += gen_family[5] - gen_family[4]   # Sum. Death Age

            female.data[gen][gsFsumMB][0] += 1   # Family Counter
            if gen_family[7] > 0 and gen_family[2] > 0:
                female.data[gen][gsFsumMB][1] += 1   # Marriage Counter
                female.data[gen][gsFsumMB][2] += gen_family[2] - gen_family[7]   # Sum. Marr. Age
            female.data[gen][gsFsumDB][0] += 1   # Family Counter
            if gen_family[7] > 0 and gen_family[8] > 0:
                female.data[gen][gsFsumDB][1] += 1   # Death Counter
                female.data[gen][gsFsumDB][2] += gen_family[8] - gen_family[7]   # Sum. Death Age

            if gen_family[9] > 0:   # Child Counter
                child.data[gen][gsCfrstMB][0] += gen_family[9]   # Child Counter
                child.data[gen][gsCfrstMB][1] += 1   # First Birth Counter
                if child.data[gen][gsCfrstMB][2] == 0:
                    child.data[gen][gsCfrstMB][2] = gen_family[11]
                if gen_family[11] > 0:   # First Birth Age
                    child.data[gen][gsCfrstMB][2] = min(child.data[gen][gsCfrstMB][2], gen_family[11])

                child.data[gen][gsCavgMB][0] += gen_family[9]   # Child Counter
                child.data[gen][gsCavgMB][1] += 1   # Birth Counter
                child.data[gen][gsCavgMB][2] += gen_family[10] / float(gen_family[9])   # Sum. Birth Age

                child.data[gen][gsClstMB][0] += gen_family[9]   # Child Counter
                child.data[gen][gsClstMB][1] += 1   # Last Birth Counter
                if child.data[gen][gsClstMB][2] == 0:
                    child.data[gen][gsClstMB][2] = gen_family[12]
                if child.data[gen][gsClstMB][2] < gen_family[12]:   # Last Birth Age
                    child.data[gen][gsClstMB][2] = gen_family[12]

            gen0 = gen

        if debug: text_list += '\n'

        return text_list

    def analyse2_gen_stat(self, max_gen, male, female, child):
        """"""
        low, high = 0, max_gen
        for gen in range (1, max_gen -1):
            low = gen
            if (male.data[gen][gsMsumMB][1] > 0 or male.data[gen][gsMsumDB][1] > 0): break
        for gen in range (max_gen -1, 1, -1):
            high = gen
            if (male.data[gen][gsMsumMB][1] > 0 or male.data[gen][gsMsumDB][1] > 0): break
        for evt in [gsMsumMB, gsMsumDB]:   # 1: Marriage, 2: Death
            male = self.norm_gen_stat(low, high, male, evt)

        low, high = 0, max_gen
        for gen in range (1, max_gen -1):
            low = gen
            if (female.data[gen][gsFsumMB][1] > 0 or female.data[gen][gsFsumDB][1] > 0): break
        for gen in range (max_gen -1, 1, -1):
            high = gen
            if (female.data[gen][gsFsumMB][1] > 0 or female.data[gen][gsFsumDB][1] > 0): break
        for evt in [gsFsumMB, gsFsumDB]:   # 1: Marriage, 2: Death
            female = self.norm_gen_stat(low, high, female, evt)

        low, high = 0, max_gen
        for gen in range (1, max_gen -1):
            low = gen
            if (child.data[gen][gsCavgMB][1] > 0 or child.data[gen][gsCsumDB][1] > 0): break
        for gen in range (max_gen -1, 1, -1):
            high = gen
            if (child.data[gen][gsCavgMB][1] > 0 or child.data[gen][gsCsumDB][1] > 0): break
        for evt in [gsCavgMB, gsCsumDB]:   # 1: Born, 3: Death
            child = self.norm_gen_stat(low, high, child, evt)

        text_list = self.apply_gen_stat(low, high, male, female, child)

        return text_list

    def write_gen_stat(self, text_list1, text_list2, text_list3=None):
        """"""

        def push_textlist(text_list, indent='', close=''):
            """"""
            for text_line in text_list:
                if text_line: self.genstat_file.writelines(indent + text_line +  close)

        ext = '_G{}'.format(self.datadict['grade'])
        path_name, report_text = \
            apply_filehead('D', self.database, self.datadict['pid'], self.datadict['resultpath'], 'Statistik', 'GenStat', 'dat', ext)
        self.genstat_file = open(path_name, mode='w', buffering=1)

        self.genstat_file.writelines('# {} (Grad {})\n\n'.format(report_text, self.datadict['grade']))
        self.genstat_file.writelines('# Raw   Personen (Male, Female):        {} / ({})\n' \
                                     .format(self.datadict['rawMale'], self.datadict['rawFemale']))
        self.genstat_file.writelines('# Calc. Personen (Male, Female, Child): {} / {} / {} = {}\n' \
                                     .format(self.datadict['calcMale'], self.datadict['calcFemale'], self.datadict['calcChild'], \
                                      self.datadict['calcMale'] + self.datadict['calcFemale'] + self.datadict['calcChild']))
        self.genstat_file.writelines('# Calc. Familien:                       {}\n\n' \
                                     .format(self.datadict['calcFamily']))

        push_textlist(text_list1)
        if text_list3:
            self.genstat_file.writelines('\n')
            push_textlist(text_list3)
        self.genstat_file.writelines('\n')
        push_textlist(text_list2)

        self.genstat_file.close()

        return

    def find_marriage_date(self, family):
        """Determines a family's marriage date"""

        if not family: return 0

        mdate = 0
        date_options = {'endnote': False, 'year_only': True}
        marriage = ReportUtils.find_marriage(self.database, family)
        if marriage:
            mdate = marriage.get_date_object().get_year()
        if mdate == 0:
            min_bdate = 0
            for child_ref in family.get_child_ref_list():   # check all kids, may not be in line
                child_handle = child_ref.ref
                if child_handle:
                    child = self.database.get_person_from_handle(child_handle)
                    child_bdate, __ = determine_birthdate (self.database, child, date_options)
                    if min_bdate == 0: min_bdate = child_bdate
                    if child_bdate > 0:
                        min_bdate = min(min_bdate, child_bdate)
            if min_bdate > 0:   #  calculated & estimated marriage date
                mdate = min_bdate -1

        return mdate
