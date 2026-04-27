# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2022  Alois Poettker
#

"Import ProGen Report in Gramps"

#-------------------------------------------------------------------------
#
# standard python modules
#
#-------------------------------------------------------------------------
# import logging

# LOG = logging.getLogger('.ImportProGenText')

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

from gramps.gen.db import DbTxn
from gramps.plugins.libAP.libbase import *
from gramps.plugins.moduleAP.completenames import *
from gramps.gen.lib import (AttributeType,
                            Citation)

# --------------------------------------------------------------------------
class CompleteSourceCitation:

    def __init__(self, database, default):
        """"""
        self.database = database
        self.default = default

        if self.default['base']['analyze_enable']:
            if self.default['base']['analyze_file'][-4:] != ".txt":
                self.default['base']['analyze_file'] += ".txt"
            self.analyze_handle = open(self.default['base']['analyze_file'], 'w')
            self.analyze_handle.write("Start\n\n")

        if self.default['base']['analyze_enable']:
            self.analyze_handle.write("End\n")
            self.analyze_handle.close()


    # Citation - Attribute ---------------------------------------------------------------------------------------------- #
    def determine_attribute(self, source, matrikel, date):
        """"""
        key_string = None
        matriken = {
            "Taufen": {
                'KB01_01': {'von': 1639, 'bis': 1664},
                'KB02_01': {'von': 1665, 'bis': 1684},
                'KB03_01': {'von': 1685, 'bis': 1712},
                'KB04_01': {'von': 1713, 'bis': 1737},
                'KB05_01': {'von': 1738, 'bis': 1767},
                'KB06_01': {'von': 1768, 'bis': 1795},
                'KB07_01': {'von': 1796, 'bis': 1811},
                'KB08'   : {'von': 1812, 'bis': 1837},
                'KB11'   : {'von': 1838, 'bis': 1861},
                'KB14'   : {'von': 1862, 'bis': 1884},
                'KB19'   : {'von': 1885, 'bis': 1907},
            },
            "Trauungen": {
                'KB01_02': {'von': 1639, 'bis': 1664},
                'KB02_02': {'von': 1665, 'bis': 1684},
                'KB03_02': {'von': 1685, 'bis': 1712},
                'KB04_02': {'von': 1713, 'bis': 1737},
                'KB05_02': {'von': 1738, 'bis': 1767},
                'KB06_02': {'von': 1768, 'bis': 1795},
                'KB07_02': {'von': 1796, 'bis': 1811},
                'KB09'   : {'von': 1812, 'bis': 1837},
                'KB12'   : {'von': 1838, 'bis': 1861},
                'KB15'   : {'von': 1862, 'bis': 1882},
                'KB17'   : {'von': 1883, 'bis': 1905},
                'KB21'   : {'von': 1906, 'bis': 1928}
            },
            "Beerdigungen": {
                'KB01_03': {'von': 1644, 'bis': 1663},
                'KB02_03': {'von': 1664, 'bis': 1684},
                'KB03_03': {'von': 1685, 'bis': 1712},
                'KB04_03': {'von': 1713, 'bis': 1737},
                'KB05_03': {'von': 1738, 'bis': 1767},
                'KB06_03': {'von': 1768, 'bis': 1795},
                'KB07_03': {'von': 1796, 'bis': 1811},
                'KB10'   : {'von': 1812, 'bis': 1837},
                'KB13'   : {'von': 1838, 'bis': 1861},
                'KB16'   : {'von': 1862, 'bis': 1882},
                'KB18'   : {'von': 1883, 'bis': 1904},
                'KB20'   : {'von': 1905, 'bis': 1929}
            }
        }

        def get_matrikel(matrikel, date):
            """"""
            for k, v in matrikel.items():
                if v['von'] <= date <= v['bis']:
                    return k
            return None

        if matrikel == 'Taufregister': key_string = 'Taufen'
        elif matrikel == 'Trauregister': key_string = 'Trauungen'
        elif matrikel == 'Sterberegister': key_string = 'Beerdigungen'

        attr_string = source
        if key_string:
            key = get_matrikel(matriken[key_string], date)
            if key:
                attr_string += ' %s, %s, %s - %s' % \
                    (key, key_string, matriken[key_string][key]['von'], matriken[key_string][key]['bis'])
        source_attr = create_srcattribute("Matrikel", attr_string)

        return source_attr

    # Citation - Name --------------------------------------------------------------------------------------------------- #
    def complete_citation_personname(self, person, handle):
        """"""
        altnames_list = person.get_alternate_names()

        firstname = person.get_primary_name()
        firstname_str = firstname.get_type().string
        if firstname_str != SUBST_NAMETYPE or len(altnames_list) == 0:
            firstname.add_citation(handle)

        for nr, altname in enumerate(altnames_list):
            altname_str = altname.get_type().string
            altname_cit = altname.get_citation_list()
            if altname_str != SUBST_NAMETYPE and len(altname_cit) == 0:
                altname.add_citation(handle)

    def create_citation_familyname(self, family):
        """"""
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

        return father_surname, mother_surname


    # Citation ---------------------------------------------------------------------------------------------------------- #
    def create_citation_page(self, objekt, export, first, second, length=5, cit_type=''):
        """"""
        page = ''
        if export: page = '%s %s' % (self.default['citation']['title'], self.default['source']['date'])
        if objekt: page += ' [ID: %s%s]' % (objekt.gramps_id[0], objekt.gramps_id[1:].zfill(length))
        if cit_type: page += cit_type
        if second: page += ' %s' % second if second else ' N.N.'
        page += ',' if objekt.gramps_id[0] == 'I' else ' --'
        page += ' %s' % first if first else ' N.N.'

        return page

    def determine_citation_date(self, citation, event, rule=False):
        """"""
        if citation.date.is_empty() or '-' in citation.date.text or rule:
            if event: citation.set_date_object(event.date)
        else:
            citation.date.set_modifier(Date.MOD_NONE)
            if 'ca.' in citation.date.text:
                citation.date.set_quality(Date.QUAL_ESTIMATED)
                citation.date.text = citation.date.text.replace('ca.', '').strip()
            date, year, month, day = create_date_from_text(citation.date.text)
            citation.date.set_yr_mon_day(year, month, day, True)
            citation.date.set_text_value('')

    def determine_object_type(self, string):
        """"""
        type_string = ''

        # Source
        if 'Taufregister' in string: type_string = 'Taufregister'
        elif 'Trauregister' in string: type_string = 'Trauregister'
        elif 'Sterberegister' in string: type_string = 'Sterberegister'

        # Citation
        if string in ['Geburt', 'Kleinkindtaufe']: type_string = 'Taufregister'
        elif string in ['Hochzeit', 'Trauung']: type_string = 'Trauregister'
        elif string in ['Tod', 'Beerdigung']: type_string = 'Sterberegister'

        return type_string, string

    def create_citation(self, source, date, confidence, page, attribute=None):
        """"""
        citation = Citation()
        if source: citation.set_reference_handle(source)
        citation.set_date_object(date)
        citation.set_confidence_level(confidence)
        citation.set_page(page)
        if attribute: citation.add_attribute(attribute)

        return citation


    # Event - Citation -------------------------------------------------------------------------------------------------- #
    def determine_citation_partpage(self, event):
        """"""
        if not event: return ''

        partpage = ''
        if event and event.handle:
            event_handle_list = list(self.database.find_backlink_handles(event.handle))

        if event_handle_list:
            for (reference_class_name, reference_handle) in event_handle_list:
                if reference_class_name == 'Person':
                    person = self.database.get_person_from_handle(reference_handle)
                    firstnames, surname = ordName(person).get_citationname()
                    partpage += self.create_citation_page('I', None, None, firstnames, surname, length=4)
                elif reference_class_name == 'Family':
                    family = self.database.get_family_from_handle(reference_handle)
                    father_surname, mother_surname = self.create_family_citation(family)
                    partpage += self.create_citation_page('F', None, None, mother_surname, father_surname)   # Twisted!

        return partpage.strip()

    def compare_event_citations(self, citation1, citation2):
        """"""
        equality = True;

        equality &= citation1.gramps_id != citation2.gramps_id
        equality &= citation1.page == citation2.page
        equality &= citation1.source_handle == citation2.source_handle

        return equality

    def complete_event_citation(self):
        """ Perform the completion of Citation. """
        self.database.disable_signals()

        attribute = create_srcattribute("Citation", self.citation_attribute)

        _debug_ = False

        citation_start, citation_stop = 0, 9   # 9999
        citation_handle_list = list(self.database.iter_citation_handles())
        for citation_idx, citation_handle in enumerate(citation_handle_list[citation_start:], start = citation_start):
            if citation_idx > citation_start + citation_stop -1: break
            citation = self.database.get_citation_from_handle(citation_handle)
            if citation is None: continue

            # Check auf Quellentitel
            source = self.database.get_source_from_handle(citation.source_handle)
            if source.title != self.default['source']['title']: continue

            # Check auf Quellentitel
            source = self.database.get_source_from_handle(citation.source_handle)

            # Check auf Verweisseite
            page = citation.get_page()
            if page and page[0] == '[': continue

            # Confidence
            citation.confidence = 1
            citation_type = ''

            # Eventholung
            event, event_handle_list = None, None
            object_handle_list = list(self.database.find_backlink_handles(citation_handle))
            if object_handle_list:
                if object_handle_list[0][0] == "Event":
                    event = self.database.get_event_from_handle(object_handle_list[0][1])
                    citation.date = event.date
                    if 'Standesamt' in source.title:
                        citation.confidence = 3
                        if event.type.string == 'Geburt':
                            citation_type = 'Geburtsregister'
                        elif event.type.string == 'Hochzeit':
                            citation_type = 'Heiratsregister'
                        elif event.type.string in ['Beerdigung', 'Tod']:
                            citation_type = 'Sterberegister'
                        else:
                            citation.confidence = 1
                    elif 'BA' in source.title or \
                         'Kirchenbuch' in source.title:
                        if event.type.string in ['Geburt', 'Kleinkindtaufe']:
                            citation_type = 'Taufregister'
                            if 'Geburts- und Taufbuch' in citation.page:
                                citation.page = citation.page.replace('Geburts- und Taufbuch', 'Taufregister').strip()
                                citation_type = '???'
                            elif 'Tauf- Register' in citation.page:
                                citation.page = citation.page.replace('Tauf- Register', 'Taufregister').strip()
                                citation_type = '???'
                            elif 'Taufregister' in citation.page:
                                citation_type = '???'
                            else:
                                citation.confidence = 3
                        elif event.type.string in ['Hochzeit', 'Trauung']:
                            citation_type = 'Trauregister'
                            if 'Heiratsregister' in citation.page:
                                citation.page = citation.page.replace('Heiratsregister', 'Trauregister').strip()
                                citation_type = '???'
                            elif 'Trauregister' in citation.page:
                                citation_type = ''
                                citation.confidence = 3
                            else:
                                citation.confidence = 3
                        elif event.type.string in ['Beerdigung', 'Tod']:
                            citation_type = 'Sterberegister'
                            if 'Sterberegister' in citation.page:
                                citation_type = '???'
                            else:
                                citation.confidence = 3
                        else:
                            citation_type = '???'

            if event and event.handle:
                event_handle_list = list(self.database.find_backlink_handles(event.handle))

            # Attributergaenzung
            cattr = [attr for attr in citation.attribute_list if self.citation_attribute in attr.value]
            if not cattr: citation.add_attribute(attribute)

            if event_handle_list:
                for (reference_class_name, reference_handle) in event_handle_list:
                    if reference_class_name == 'Person':
                        person = self.database.get_person_from_handle(reference_handle)
                        firstnames, surname = ordName(person).get_citationname()
                        page = '%s %s' % (citation_type, citation.page)
                        page += self.create_citation_page('I', None, firstnames, surname, length=6)
                        citation.page = page

                        print("Ind.%i: %s" % (citation_idx, page))
                    elif reference_class_name == 'Family':
                        family = self.database.get_family_from_handle(reference_handle)
                        father_surname, mother_surname = self.create_family_citation(family)
                        page = '%s %s' % (citation_type, citation.page)
                        page += self.create_citation_page('F', None, mother_surname, father_surname)   # Twisted!
                        citation.page = page

                        print("Fam.%i: %s" % (citation_idx, page))

                    with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
                        if not _debug_:
                            self.database.commit_citation(citation, trans)

        self.database.enable_signals()
        self.database.request_rebuild()

        return True


    # Person - Citation ------------------------------------------------------------------------------------------------------ #
    def compare_person_citations(self, citation1, citation2, name):
        """"""
        equality = True;

        equality &= citation1.gramps_id != citation2.gramps_id
        if len(citation1.page) > 12 and len(citation2.page) < 13:
            cit1_page = citation1.page.split(' ')
            equality &= cit1_page[1] == citation2.page
            if '--' in cit1_page:   #  Family Father -- Mother
                equality &= (cit1_page[2] == name) or (cit1_page[4] == name)
            else:   #  Person Surname
                equality &= cit1_page[2].replace(',','') == name
        else:
            equality &= citation1.page == citation2.page

        equality &= citation1.source_handle == citation2.source_handle

        return equality

    def complete_citation_perfam(self):
        """
        Perform the completion of Citation.
        """
        _debug_ = False
        self.database.disable_signals()

        index_list = []
        index_ind, index_fam = 0, 0

        attr_text = '%s %s - %s' % (self.default['source']['attr-title'], self.default['source']['date'], \
                                           self.default['source']['attr-text'])
        citation_attribute = create_attribute(AttributeType.CUSTOM, "Quelle", attr_text)
        date, year, month, day = create_date_from_text(self.default['source']['date'])

        citation_start, citation_stop = 5, 5555   # 5555
        citation_handle_list = list(self.database.iter_citation_handles())
        for citation_idx, citation_handle in enumerate(citation_handle_list[citation_start:], start = citation_start):
            if citation_idx > citation_start + citation_stop -1: break
            citation = self.database.get_citation_from_handle(citation_handle)

            # Check auf Quellentitel
            # source = self.database.get_source_from_handle(citation.source_handle)
            # if source.title != self.default['source']['title']: continue

            # Check auf Verweisseite
            # page = citation.get_page()
            # if not 'Export' in page: continue

            object_handle_list = list(self.database.find_backlink_handles(citation_handle))
            # Verweisseitenergaenzung bei existierender ID
            """
            prepage = page.split(' [')[0]
            gramps_id = ''
            preind = page.split(' I')

            if not gramps_id:
                if len(preind) > 1:
                    prefix_str = preind[1].split(']')[0]
                    if len(prefix_str) > 5: prefix_str = prefix_str[1:]
                    gramps_id = 'I' + prefix_str.zfill(5)
            if not gramps_id:
                prefam = page.split(' F')
                if len(prefam) > 1:
                    prefix_str = prefam[1].split(']')[0]
                    if len(prefix_str) > 5: prefix_str = prefix_str[1:]
                    gramps_id = 'F' + prefix_str.zfill(5)
            page = '%s [ID: %s]' % (prepage, gramps_id)

            if gramps_id in index_list: continue   # Citation exists
            else: index_list.append(gramps_id)
            """
            # Attributergaenzung
            cattr = False
            for attr in citation.attribute_list:
                if attr_text in attr.value:
                    cattr = True
                    break

            # Referenznamenergaenzung
            for (reference_class_name, reference_handle) in object_handle_list:
                if reference_class_name == 'Person':
                    person = self.database.get_person_from_handle(reference_handle)
                    if person.gramps_id in index_list:
                        pass   # Citation exists
                    else: index_list.append(person.gramps_id)

                    index_ind += 1
                    ord_name = ordName(person)
                    firstnames, surname = ord_name.get_citationname()
                    page = self.create_citation_page(person, True, firstnames, surname)
                    # attr = create_srcattribute(AttributeType.CUSTOM, 'REFN', person.gramps_id)
                    print("Cit. Ind. %i: %s" % (index_ind, page))

                if reference_class_name == 'Family':
                    family = self.database.get_family_from_handle(reference_handle)
                    if family.gramps_id in index_list:
                        continue   # Citation exists
                    else: index_list.append(family.gramps_id)

                    index_fam += 1
                    father_surname, mother_surname = self.create_citation_familyname(family)
                    page = self.create_citation_page(family, True, mother_surname, father_surname, length=4)
                    # attr = create_srcattribute(AttributeType.CUSTOM, 'REFN', family.gramps_id)
                    print("Cit. Fam. %i: %s" % (index_fam, page))

                if reference_class_name == 'Person' or \
                   reference_class_name == 'Family':
                    citation.set_date_object(date)
                    citation.set_page(page)
                    citation.set_confidence_level(self.default['citation']['confidence'])
                    # citation.add_attribute(attr)
                    if not cattr:
                        citation.add_attribute(citation_attribute)

                    with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
                        if not _debug_ : self.database.commit_citation(citation, trans)

        self.database.enable_signals()
        self.database.request_rebuild()

        return True

    # Family - Citation ------------------------------------------------------------------------------------------------------ #

    # One-Shot - Citation ---------------------------------------------------------------------------------------------------- #
    def cleanup_citation(self):
        """
        Perform the cleanup of Citation.
        """
        _debug_ = False
        self.database.disable_signals()

        citation_start, citation_stop = 0, 5555   # 5555
        citation_handle_list = list(self.database.iter_citation_handles())
        for citation_idx, citation_handle in enumerate(citation_handle_list[citation_start:], start = citation_start):
            if citation_idx > citation_start + citation_stop -1: break
            citation = self.database.get_citation_from_handle(citation_handle)

            # Check auf Quellentitel
            source = self.database.get_source_from_handle(citation.source_handle)
            if source.title != self.default['cleanup']['title']: continue

            for attr in list(citation.attribute_list):
                if (attr.type.value == 0 and attr.type.string == "Fundstelle"):
                    citation.attribute_list.remove(attr)
                if (attr.type.value == 0 and attr.type.string == "Matrikel" and attr.value.endswith(',')):
                    citation.attribute_list.remove(attr)

            with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
                if not _debug_ : self.database.commit_citation(citation, trans)

        self.database.enable_signals()
        self.database.request_rebuild()

        return True


    def add_citation_link(self):
        """ Perform the completion of Citation. """
        _debug_ = False
        self.database.disable_signals()

        def add_link(citation, attribute, date=None):
            exist = False
            for attr in citation.attribute_list:
                if attribute.value in attr.value:
                    exist = True
                    break

            if not exist:
                citation.add_attribute(attribute)

            return exist

        # Quellen
        source = self.database.get_source_from_gramps_id(self.default['source']['id'])
        if not self.default['source']['title'] in source.title:
            return False

        src_attr = SrcAttribute()
        src_attr.set_type(self.default['citation']['attr-type'])
        src_attr.set_value(self.default['citation']['attr-value'])

        citation_start, citation_stop = 0, 5555
        citation_handle_list = list(self.database.find_backlink_handles (source.handle))

        with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
            number = 1
            for citation_idx, citation_handle in enumerate(citation_handle_list[citation_start:], start = citation_start):
                if citation_idx > citation_start + citation_stop -1: break

                if citation_handle[0] == u'Citation':
                    citation = self.database.get_citation_from_handle(citation_handle[1])
                else: continue

                if not self.default['citation']['date'] in citation.page:
                    continue

                if self.default['base']['job'] == 'add-link':
                    exist = add_link(citation, src_attr)

                if not exist:
                    if not _debug_ :
                        self.database.commit_citation(citation, trans)
                    print("%04i: Cit. %04i - %s" % (number, citation_idx, citation.gramps_id))
                    number += 1

        self.database.enable_signals()
        self.database.request_rebuild()

        return True

    def modify_citation_BJJ(self):
        """ Perform the completion of Bernd-Josef Jansen Citation. """
        self.database.disable_signals()
        confidence = 3
        citation_handle_list = list(self.database.iter_citation_handles())

        index_ges = 0
        index_dict = defaultdict()
        for citation_handle in citation_handle_list:
            citation = self.database.get_citation_from_handle(citation_handle)
            if citation is None:
                continue

            # Check auf Quellentitel
            source = self.database.get_source_from_handle(citation.source_handle)
            if not 'Genealogie Jansen' in source.title: continue

            # Check auf Verweisseite
            page = citation.get_page()
            if not 'WWW Abschrift' in page: continue

            index_ges += 1
            # if index_ges < 17: continue

            # Verweisseitenergaenzung
            prepage = page.split(' [')[0]
            page_split = page.split(' I')

            gramps_id = ''
            if len(page_split) > 1:
                prefix_str = page_split[1].split(']')[0]
                if len(prefix_str) > 5: prefix_str = prefix_str[1:]
                gramps_id = 'I' + prefix_str.zfill(5)
                postfix_str = page_split[1].split('] ')[1].strip()

            citation.page = '[%s] %s' % (gramps_id, postfix_str)

            # Attributergaenzung
            attr_type = "WWW Abschrift"
            attr_value = prepage.split(attr_type)[1].strip()
            sattr = SrcAttribute()
            sattr.set_type(attr_type)
            sattr.set_value(attr_value)

            exist = False
            for attr in citation.attribute_list:
                if attr_value in attr.value:
                    exist = True
                    break
            if not exist:
                citation.add_attribute(sattr)

            print("Cit. %i: %s > %s" % (index_ges, citation.gramps_id, citation.page))
            if gramps_id in index_dict:   # Citation exists
                phoenix = citation
                titanic = self.database.get_citation_from_gramps_id(index_dict[gramps_id])
                if phoenix.gramps_id != titanic.gramps_id:
                    if not _debug_:
                        query = MergeCitationQuery(self.database, phoenix, titanic)
                        query.execute()
            else:
                index_dict[gramps_id] = citation.gramps_id
                if not _debug_:
                    with DbTxn(_("Citation modification"), self.database, batch=True) as trans:
                        self.database.commit_citation(citation, trans)
                        pass

        self.database.enable_signals()
        self.database.request_rebuild()

        return True

    def create_citation_ProGen_Report(self):
        """ Perform the creation of Citation, if not Person / Family citation exist (eg. GES-2000). """
        _debug_ = True

        def extract_nid(mode, objekt, base=False):
            """"""
            nid_base, nid_ext = '', ''
            attribute_list = objekt.get_attribute_list()
            if len(attribute_list) > 0:
                for attr in attribute_list:
                    if attr.get_type().string == 'REFN':
                        if mode == 'F':
                            attr.value = attr.value.split('.', maxsplit=1)[1]
                        if base:
                            nid_base = attr.value.split('-')[0]
                        nid_ext = attr.value
                        break
            else:
                print('Error IND %s: No REFN!' % objekt.get_gramps_id())
                return '', None

            return nid_base, nid_ext

        citation_dict = {}
        cit_object, cit_person, cit_family = False, True, False
        loop_start, loop_stop = 0, 11000

        if cit_object:
            if self.default['txt_import']['import_file'][-4:] == ".txt":
                import_file = self.default['txt_import']['import_file'][:-4] + ".json"
            with open(import_file, 'r') as file_handle:
                self.descendant_dict = json.load(file_handle)

            source = self.get_source_from_id(identity=self.default['source']['id'])

            date, year, month, day = create_date_from_text(self.default['source']['date'])
            attr = '%s (%s)' % (self.default['source']['attr-text'], self.default['source']['date'])
            attribute = create_srcattribute("Quelle", attr_text=attr)

            confidence = self.default['citation']['confidence']

            person_handle_list = list(self.database.iter_person_handles())
            for person_idx, person_handle in enumerate(person_handle_list[loop_start:], start=loop_start):
                if person_idx > loop_start + loop_stop: break
                person = self.database.get_person_from_handle(person_handle)
                if person is None: continue

                nid_base, nid_ext = extract_nid('I', person, False)
                if nid_ext in self.descendant_dict:
                    if 'citname' in self.descendant_dict[nid_ext]:
                        nid_base = nid_ext.split('-')[0]
                        surname, firstnames = self.descendant_dict[nid_ext]['citname'].split(', ')

                        page = self.create_citation_page('I', True, nid_base, firstnames, surname)
                        attr = create_srcattribute(AttributeType.CUSTOM, 'REFN', nid_base)
                        citation = self.create_citation(source, date, confidence, page, attr)
                        citation.add_attribute(attribute)

                if nid_base:
                    citation_dict[nid_base] = citation
                    print("Cit. %i: %s" % (person_idx, citation.get_page()))

            self.database.disable_signals()
            with DbTxn(_("Create citation"), self.database, batch=True) as trans:
                for citation in citation_dict.values():   # store
                    if not _debug_: self.database.add_citation(citation, trans)

        if cit_person:
            citation_dict.clear()

            # get citation out of Gramps
            citation_handle_list = list(self.database.iter_citation_handles())
            for cit_handle in citation_handle_list:
                citation = self.database.get_citation_from_handle(cit_handle)
                nid_base, nid_ext = extract_nid('I', citation, True)
                citation_dict[nid_base] = citation

            person_handle_list = list(self.database.iter_person_handles())
            for person_idx, person_handle in enumerate(person_handle_list[loop_start:], start = loop_start):
                if person_idx > loop_start + loop_stop: break
                person = self.database.get_person_from_handle(person_handle)
                if person is None: continue

                nid_base, nid_ext = extract_nid('I', person, True)
                if nid_base in citation_dict:
                    citation = citation_dict[nid_base]

                    # if citation.handle: person.add_citation(citation.handle)
                    self.complete_citation_personname(person, citation.handle)

                    for event_ref in person.event_ref_list:
                        if event_ref.ref:
                            event = self.database.get_event_from_handle(event_ref.ref)
                            if citation.handle: event.add_citation(citation.handle)
                            if not _debug_: self.database.commit_event(event, trans)

                    for attr in person.attribute_list:
                        if attr.get_type().string != 'REFN':
                            if citation.handle: attr.add_citation(citation.handle)

            with DbTxn(_("Create citation"), self.database, batch=True) as trans:
                        if not _debug_: self.database.commit_person(person, trans)
                        print("Cit. Pers. %i: %s" % (person_idx, citation.get_page()))

        if cit_family:
            """
            citation_dict.clear()

            # get citation out of Gramps
            citation_handle_list = list(self.database.iter_citation_handles())
            for cit_handle in citation_handle_list:
                citation = self.database.get_citation_from_handle(cit_handle)
                nid_base, nid_ext = extract_nid('I', citation, True)
                citation_dict[nid_base] = citation
            """
            self.database.disable_signals()
            with DbTxn(_("Create citation"), self.database, batch=True) as trans:
                family_handle_list = list(self.database.iter_family_handles())
                for family_idx, family_handle in enumerate(family_handle_list[loop_start:], start = loop_start):
                    if family_idx > loop_start + loop_stop: break
                    family = self.database.get_family_from_handle(family_handle)
                    if family is None: continue

                    nid_base, nid_ext = extract_nid('F', family, True)
                    if nid_base in citation_dict:
                        citation = citation_dict[nid_base]

                        # if citation.handle: family.add_citation(citation.handle)

                        for event_ref in family.event_ref_list:
                            if event_ref.ref:
                                event = self.database.get_event_from_handle(event_ref.ref)
                                if citation.handle: event.add_citation(citation.handle)
                                if not _debug_: self.database.commit_event(event, trans)

                        for attr in family.attribute_list:
                            if attr.get_type().string != 'REFN':
                                if citation.handle: attr.add_citation(citation.handle)

                        if not _debug_: self.database.commit_family(family, trans)
                        print("Cit. Fam. %i: %s" % (family_idx, citation.get_page()))

        self.database.enable_signals()
        self.database.request_rebuild()

        return True

    def create_citation_ProGen_Export(self):
        """
        Perform the completion of Citation.
        """
        _debug_ = True

        person_list = []
        index_ind, index_fam = 0, 0

        attr_text = '%s %s - %s' % (self.default['source']['attr-title'], self.default['source']['date'], \
                                           self.default['source']['attr-text'])
        citation_attribute = create_srcattribute(AttributeType.CUSTOM, "Quelle", attr_text)
        date, year, month, day = create_date_from_text(self.default['source']['date'])

        self.database.disable_signals()
        with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
            loop_start, loop_stop = 0, 11000

            person_handle_list = list(self.database.iter_person_handles())
            for person_idx, person_handle in enumerate(person_handle_list[loop_start:], start = loop_start):
                if person_idx > loop_start + loop_stop: break
                person = self.database.get_person_from_handle(person_handle)
                if person is None: continue

                firstnames, surname = ordName(person).get_citationname()
                page += self.create_citation_page('I', None, None, firstnames, surname)

                citation = self.create_citation(source, date, confidence, page)
                citation.add_attribute(attribute)

                if not _debug_: self.database.commit_person(person, trans)
                print("Cit. Pers. %i: %s" % (person_idx, citation.get_page()))

            if not _debug_ : self.database.commit_citation(citation, trans)

        self.database.enable_signals()
        self.database.request_rebuild()


    def compact_citation_Ancestry_Export(self, first=True):
        """"""
        _debug_ = False
        self.database.disable_signals()

        def init_citaton_list(first=True):
            # Preparing Citation List w/o unused items
            citation_handle_set = set(self.database.iter_citation_handles())

            self.scnd_citation_handle_list = []
            for citation_handle in citation_handle_set:
                citation = self.database.get_citation_from_handle(citation_handle)
                if citation is None: continue

                if citation.source_handle:
                    source = self.database.get_source_from_handle(citation.source_handle)
                    if 'S008' in source.gramps_id: continue

                if first: self.first_citation_dict[citation.gramps_id] = citation_handle

                if not(citation.confidence in self.citation_confidence_list): continue
                self.scnd_citation_handle_list.append(citation_handle)

        self.first_citation_dict = {}
        self.citation_confidence_list = [1, 2, 3]
        init_citaton_list(True)
        self.first_citation_dict = dict(sorted(self.first_citation_dict.items()))

        source_abbrev_list = ['B_', 'TA_', 'TR_','stA_']
        citation_confidence = Citation.CONF_VERY_HIGH
        # citation_confidence_list = [Citation.CONF_VERY_LOW, Citation.CONF_VERY_HIGH]

        citation_attribute = '%s (%s)' % (self.export_prevalue, self.export_file)
        citation_attr = self.__create_srcattribute("Citation", citation_attribute)
        citation_list = []

        scnd_counter = 0
        citation_stop = 1500
        citation_debug = None # {'first': 'C09803', 'scnd': 'C09804'}
        for first_loop, (first_citation_gramps_id, first_citation_handle) in \
            enumerate(self.first_citation_dict.items()):
            if first_loop >= citation_stop: break
            if scnd_counter >= 100: break
            if citation_debug:
                first_citation = self.database.get_citation_from_gramps_id(citation_debug['first'])
                first_citation_handle = first_citation.handle
            else:
                first_citation = self.database.get_citation_from_handle(first_citation_handle)
            if first_citation is None: continue

            if first_citation.get_confidence_level() in self.citation_confidence_list: continue

            first_source_type = None
            if first_citation.source_handle:
                first_source = self.database.get_source_from_handle(first_citation.source_handle)
                first_source_type, __ = self.determine_object_type(first_source.title)

            first_citation_type, first_partpage = None, None
            first_object_handle_list = list(self.database.find_backlink_handles(first_citation_handle))
            if not first_object_handle_list: continue

            """
            if first_object_handle_list[0][0] == 'Person':
                first_person = self.database.get_person_from_handle(first_object_handle_list[0][1])
                if first_person:
                    first_citation_type = first_source_type
                    if first_source_type == 'Taufregister' and first_person.event_ref_list:
                        first_event, __ = determine_specific_event \
                            (self.database, first_person, EventType.CHRISTEN, [EventRoleType.PRIMARY])
                        if not first_event:
                            first_event, __ = determine_specific_event \
                                (self.database, first_person, EventType.BIRTH, [EventRoleType.PRIMARY])
                    if first_source_type == 'Trauregister' and first_person.family_list:
                        for familiy_handle in first_person.family_list:
                            first_family = self.database.get_family_from_handle(familiy_handle)
                            first_event, __ = determine_specific_event \
                                (self.database, first_family, EventType.MARRIAGE, [EventRoleType.FAMILY])
                    if first_source_type == '' and first_person.event_ref_list:
                        first_citation_type == 'Person'
                        a = 1
            """
            first_event = None
            if len(first_citation.page) > 12:
                if any(element in first_citation.page for element in source_abbrev_list): continue
                citation_page = first_citation.page

            elif first_object_handle_list[0][0] == 'Event':
                first_event = self.database.get_event_from_handle(first_object_handle_list[0][1])
                first_citation_type, __ = self.determine_object_type(first_event.type.string)
                first_partpage = self.determine_citation_partpage(first_event)
                self.determine_citation_date(first_citation, first_event)

                first_orgpage = first_citation.page.replace('/-', '').strip() \
                    if '/-' in first_citation.page else first_citation.page
                citation_page = '%s %s %s' % \
                    (first_citation_type, first_orgpage, first_partpage)

                first_citation.set_confidence_level(citation_confidence)
                if first_source_type and (first_source_type != first_citation_type):
                    first_citation.set_confidence_level(Citation.CONF_VERY_LOW)

                if any(element in first_orgpage for element in source_abbrev_list):
                    first_citation.set_confidence_level(Citation.CONF_VERY_LOW)

                source_attr = self.determine_attribute \
                    ('St. Vitus Löningen,', first_citation_type, first_citation.date.get_year())
                first_citation.add_attribute(source_attr)
                first_citation.add_attribute(citation_attr)

                if not(first_citation_type and first_partpage): continue

            else:
                break

            first_loop += 1
            print ('Expand citation: %s. %s (%s)' % \
                   (first_loop, first_citation.gramps_id, citation_page))

            scnd_loop = 0
            for scnd_citation_handle in self.scnd_citation_handle_list:
                if citation_debug:
                    scnd_citation = self.database.get_citation_from_gramps_id(citation_debug['scnd'])
                else:
                    scnd_citation = self.database.get_citation_from_handle(scnd_citation_handle)
                if scnd_citation is None: continue

                scnd_loop += 1
                scnd_object_handle_list = list(self.database.find_backlink_handles(scnd_citation_handle))
                if not scnd_object_handle_list: continue

                scnd_success = False
                if scnd_object_handle_list[0][0] == 'Event':
                    equality = self.compare_event_citations(first_citation, scnd_citation)
                    if equality:
                        scnd_event = self.database.get_event_from_handle(scnd_object_handle_list[0][1])
                        scnd_citation_type, scnd_event_type = self.determine_object_type(scnd_event.type.string)
                        sncd_partpage = self.determine_citation_partpage(scnd_event)

                        if scnd_event_type in ['Kleinkindtaufe', 'Beerdigung']:
                            self.determine_citation_date(first_citation, scnd_event, True)

                        if (first_citation_type != scnd_citation_type) or \
                           (first_partpage != sncd_partpage): continue
                        first_citation.set_page(citation_page)

                        scnd_success = True

                if scnd_object_handle_list[0][0] == 'Person':
                    scnd_person = self.database.get_person_from_handle(scnd_object_handle_list[0][1])
                    __, surname = ordName(scnd_person).get_citationname()
                    equality = self.compare_person_citations(first_citation, scnd_citation, surname)
                    if equality:
                        scnd_citation.page = scnd_citation.page.replace('/-', '').strip() \
                            if '/-' in scnd_citation.page else scnd_citation.page

                        scnd_counter += 1
                        print('-> %s. found: 1P: %s, 2P: %s, N: %s' %  (scnd_counter, first_citation.page, scnd_citation.page, surname))
                        scnd_success = True

                if scnd_success:
                    if not _debug_:
                        query = MergeCitationQuery(self.dbstate, first_citation, scnd_citation)
                        query.execute()

                    init_citaton_list(False)

                    print ('-> merged: 2. %s (%s - %s)' % \
                           (scnd_loop, first_citation.gramps_id, scnd_citation.gramps_id))

            if first_citation.get_confidence_level() in self.citation_confidence_list:
                first_citation.set_page(citation_page)
                citation_list.append(first_citation)

        if not _debug_ and citation_list:
            with DbTxn(_("Citation completion"), self.database, batch=True) as trans:
                print('Modifying database ...')
                for citation in citation_list:
                    self.database.commit_citation(citation, trans)
                print('Done!')

        self.database.enable_signals()
        self.database.request_rebuild()



    # Source ================================================================================================================= #
    def get_source_from_id(self, identity=None, title=None):
        """"""
        source_handle = None
        source_handle_list = list(self.database.iter_source_handles())
        for source_handle in source_handle_list:
            source = self.database.get_source_from_handle(source_handle)
            if source is None: continue

            if identity:
                if source.gramps_id == identity: break
            elif title:
                if source.title == title: break

        return source_handle

    def compare_sources(self, source1, source2):
        """"""
        equality = True;

        equality &= source1.gramps_id != source2.gramps_id
        equality &= source1.abbrev == source2.abbrev
        equality &= source1.author == source2.author
        equality &= source1.pubinfo == source2.pubinfo
        equality &= source1.title == source2.title

        return equality

    def complete_source(self):
        """
        Perform the completion of source.
        """
        _debug_ = False
        self.database.disable_signals()
        source_handle_list = list(self.database.iter_source_handles())

        with DbTxn(_("Source completion"), self.database, batch=True) as trans:
            for nr, source_handle in enumerate(source_handle_list):
                source = self.database.get_source_from_handle(source_handle)

                if source.title != '@S0088@': continue
                source.title = self.default['source']['title']
                source.author = self.default['source']['author']

                source_text = '%s %s - %s' % (self.default['source']['attr-title'], self.default['source']['date'], \
                                                   self.default['source']['attr-text'])
                source_attr = create_srcattribute(AttributeType.CUSTOM, "Quelle", source_text)
                source.add_attribute(source_attr)

                if not _debug_: self.database.commit_source(source, trans)
                print ("Src. %s: %s" % (nr, self.default['source']['title']))

        self.database.enable_signals()
        self.database.request_rebuild()

    def compact_source(self):
        """"""
        source_idx = 0
        source_handle_set = set(self.database.iter_source_handles())

        self.database.disable_signals()
        while source_handle_set:
            source_handle = source_handle_set.pop()
            source = self.database.get_source_from_handle(source_handle)
            if source is None: continue

            source_idx += 1
            for target_handle in list(self.database.iter_source_handles()):
                target = self.database.get_source_from_handle(target_handle)
                if target is None: continue

                equality = self.compare_sources(source, target)
                if equality:
                    query = MergeSourceQuery(self.dbstate, source, target)
                    if not _debug_: query.execute()
                    if target_handle in source_handle_set:
                        source_handle_set.remove(target_handle)

                    print ('Merge source: %s. %s' % (source_idx, source.get_title()))

        self.database.enable_signals()
        self.database.request_rebuild()
