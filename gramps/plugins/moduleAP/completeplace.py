# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025   Alois Poettker
#

#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------

from collections import defaultdict

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.sgettext
ngettext = glocale.translation.ngettext # else "nearby" comments are ignored

from gramps.gen.db import DbTxn
from gramps.gen.lib import (Place, PlaceName)

_DEBUG_ = False

class CompletePlace:
    """"""
    def __init__(self, database, substitute):
        """"""
        self.database = database
        self.substitute = substitute

        self.map = None
        self.__create_place_map()

    def __create_place_map(self):
            # look for existing place titles, build a map
        print('Building Place Map ...')
        self.map = defaultdict(list)
        cursor = self.database.get_place_cursor()
        data = next(cursor)
        while data:
            (handle, val) = data
            self.map[val.gramps_id] = handle
            data = next(cursor)
        cursor.close()

    def get_or_create_place(self, place_name):
        """
        Finds or creates a Place based on the place name.
        """
        if not place_name: return None

        if place_name in self.map:
            place = self.database.get_place_from_handle(self.map[place_name])
        else:
            # create a new Place
            place = Place()
            place.set_name(PlaceName(value=place_name))
            place.set_title(place_name)

            if not _DEBUG_:
                with DbTxn(_("Place creation"), self.database, batch=True) as trans:
                    self.database.add_place(place, trans)   # add & commit ...

            self.map[place_name] = place.get_handle()

        return place

def reorganise_place(self):
    """
    Check and reorganizes Places.
    """
    country_list = ['Deutschland', 'Kentucky', 'KY','Ohio', 'USA']
    add_place_dict, merge_place_dict = {}, {}
    root = Node("root")

    place_start, place_stop = 0, 999
    place_handle_list = list(self.database.iter_place_handles())
    for place_idx, place_handle in enumerate(place_handle_list[place_start:place_stop], start = place_start):
        place = self.database.get_place_from_handle(place_handle) \
            if place_handle else None
        if not place: continue

        place_name = place.get_name().value
        place_name = place_name.strip('.')
        place_name = replace_all(place_name, PLACE_DICT)
        place_name_list = place_name.split(', ')
        for plc_idx, plc_nme in enumerate(place_name_list):
            place_name_list[plc_idx] = plc_nme.strip()
        match = [country for country in country_list if country in place_name_list]

        if match:
            place_name_list.reverse()
            for plc_idx, plc_name in enumerate(place_name_list):
                plc_name = plc_name.strip()
                if not re.search('[a-zA-Z]', plc_name): continue

                if plc_idx == len(place_name_list) -1:
                    if plc_name and (plc_name not in add_place_dict):
                        plc = copy.deepcopy(place)
                        plc.name.value = plc_name
                        plc.title = plc_name
                    else:
                        plc = add_place_dict[plc_name]
                        plc.placeref_list.extend(place.placeref_list)
                else:
                    plc = self.__create_place(plc_name)

                if not search.find_by_attr(root, plc_name):
                    if plc_idx == 0:
                        node = Node(plc_name, parent=root, org_ref=[])
                    else:
                        parent = search.find_by_attr(root, place_name_list[plc_idx -1])
                        node = Node(plc_name, parent=parent, org_ref=[])
                    if plc_idx == len(place_name_list) -1:
                        node.org_ref.append(place_handle)
                else:
                    if plc_idx == len(place_name_list) -1:
                        node = search.find_by_attr(root, place_name_list[plc_idx])
                        node.org_ref.append(place_handle)

                if plc_name and (plc_name not in add_place_dict):
                    add_place_dict[plc_name] = plc
                    print ('Add place: %s. %s' % (place_idx, plc_name))

    print(RenderTree(root))

    if add_place_dict:
        idx = 0
        with DbTxn(_("Place completion"), self.database, batch=True) as trans:
            for node in PreOrderIter(root):
                if node.name == 'root': continue
                if node.name in self.map: continue

                if not node.org_ref:   # New place!
                    place = self.__create_place(node.name)

                    if not _DEBUG_: self.database.add_place(place, trans)   # add & commit ...
                    self.map[node.name] = place.get_handle()

                    print ('Add place: %s. %s' % (idx, place.get_title()))
                else:   # Rename place, connect to parent!
                    place = self.database.get_place_from_handle(node.org_ref[0]) \
                        if node.org_ref[0] else None
                    if not place: continue
                    place.name.set_value(node.name)
                    place.set_title(node.name)

                    plc_path = search.find_by_attr(root, node.name)
                    parent_pathes = util.commonancestors(plc_path)
                    parent_name = parent_pathes[-1].name
                    if parent_name != 'root':
                        parent_handle = self.map[parent_name]
                        if parent_handle and not parent_handle in place.placeref_list:
                            placeref = PlaceRef()
                            placeref.ref = parent_handle
                            place.set_placeref_list([placeref])

                    if not _DEBUG_: self.database.commit_place(place, trans)   # commit ...
                    print ('Change place: %s. %s' % (idx, place.get_title()))

                del(add_place_dict[node.name])
                idx += 1

            for key, value in add_place_dict.items():
                node = search.find_by_attr(root, key)
                parent_node = util.commonancestors(node)
                parent_name = parent_node[-1].name
                if parent_name != 'root':
                    parent_handle = self.map[parent_name]
                    if parent_handle and not parent_handle in value.placeref_list:
                        placeref = PlaceRef()
                        placeref.ref = parent_handle
                        value.set_placeref_list([placeref])

                    value.name.set_value(node.name)
                    value.set_title(node.name)
                    if not _DEBUG_: self.database.add_place(value, trans)   # add & commit ...
                    self.map[key] = value.get_handle()

                    if not node.org_ref:
                        merge_place_dict[key] = [value.get_handle(), node.org_ref]

                    print ('Change place: %s. %s' % (idx, value.get_title()))
                    idx += 1

            add_place_dict.clear()

    if merge_place_dict:
        idx = 0
        for key in merge_place_dict:
            phoenix_handle = merge_place_dict[key][0]
            phoenix = self.database.get_place_from_handle(phoenix_handle) \
                if phoenix_handle else None
            if not phoenix: continue

            for mergeref in merge_place_dict[key][1]:
                titanic = self.database.get_place_from_handle(mergeref) \
                    if mergeref else None
                if not titanic: continue

                if not _DEBUG_:
                    query = MergePlaceQuery(self.dbstate, phoenix, titanic)
                    query.execute()
                    print ('Merge place: %s. %s -> %s' % (idx, titanic.get_title(), phoenix.get_title()))
                idx += 1

    self.database.enable_signals()
    self.database.request_rebuild()

