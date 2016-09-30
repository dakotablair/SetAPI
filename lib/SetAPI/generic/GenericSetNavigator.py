


from biokbase.workspace.client import Workspace

from pprint import pprint



class GenericSetNavigator:


    SET_TYPES = ['KBaseSets.ReadsSet']


    def __init__(self, workspace_client):
        self.ws = workspace_client

    def list_sets(self, params):
        '''
        Get a list of the top-level sets (that is, sets that are unreferenced by
        any other sets in the specified workspace). Set item references are always
        returned, ws info for each of those items can optionally be included too.
        '''
        self._validate_list_params(params)

        workspace = params['workspace']
        all_sets = self._list_all_sets(workspace)
        all_sets = self._populate_set_refs(all_sets)

        # the top level sets list includes not just the set info, but
        # the list of obj refs contained in each of those sets
        top_level_sets = self._get_top_level_sets(all_sets)

        if 'include_set_item_info' in params and params['include_set_item_info']==1:
            top_level_sets = self._populate_set_item_info(top_level_sets)

        return {'sets': top_level_sets}


    def _validate_list_params(self, params):
        if 'workspace' not in params:
            raise ValueError('"workspace" field required to list sets')

        if 'include_set_item_info' in params and params['include_set_item_info'] is not None:
            if params['include_set_item_info'] not in [0,1]:
                raise ValueError('"include_set_item_info" field must be set to 0 or 1')


    def _list_all_sets(self, workspace):
        ws_info = self._get_workspace_info(workspace)
        max_id = ws_info[4]

        list_params = { 'includeMetadata': 1 }
        if str(workspace).isdigit():
            list_params['ids'] = [ int(workspace) ]
        else:
            list_params['workspaces'] = [workspace]

        sets = []
        for t in GenericSetNavigator.SET_TYPES:
            list_params['type'] = t
            sets_of_type_t = self._list_until_exhausted(list_params, max_id)
            for s in sets_of_type_t:
                sets.append({
                        'ref': self._build_obj_ref(s),
                        'info': s
                    })
        return sets


    def _get_workspace_info(self, workspace):
        # typedef tuple<ws_id 0:id, ws_name 1:workspace, username 2:owner, timestamp 3:moddate,
        # int 4max_objid, permission 5user_permission, permission 6globalread,
        # lock_status 7lockstat, usermeta 8metadata> workspace_info;
        ws_identity = {}
        if str(workspace).isdigit():
            ws_identity['id'] = int(workspace)
        else:
            ws_identity['workspace'] = workspace
        return self.ws.get_workspace_info(ws_identity)



    def _list_until_exhausted(self, options, max_id):
        min_id = 0
        step = 10000
        obj_info_list = []
        while min_id < max_id:
            options['minObjectID'] = min_id
            options['maxObjectID'] = min_id + step
            min_id = min_id + step
            result = self.ws.list_objects(options)
            obj_info_list.extend(result)
        return obj_info_list


    def _get_top_level_sets(self, set_list):
        '''
        Assumes set_list items are populated, kicks out any set that
        is directly referenced by another set on the list.
        '''

        # create lookup hash for the sets
        set_ref_lookup = {}
        for s in set_list:
            set_ref_lookup[s['ref']] = 1

        # create a lookup to identify non-root sets
        sets_referenced_by_another_set = {}
        for s in set_list:
            for i in s['items']:
                if i['ref'] in set_ref_lookup:
                    sets_referenced_by_another_set[i['ref']] = 1

        # only add the sets that are root in this WS
        top_level_sets = []
        for s in set_list:
            if s['ref'] in sets_referenced_by_another_set:
                continue
            top_level_sets.append(s)

        return top_level_sets




    def _populate_set_refs(self, set_list):

        objects = []
        for s in set_list:
            objects.append({'ref':s['ref']})
        obj_data = self.ws.get_objects2({
                'objects':objects,
                'no_data':1
            })['data']

        # if ws call worked, then len(obj_data)==len(set_list)
        for k in range(0,len(obj_data)):
            items = []
            for item_ref in obj_data[k]['refs']:
                items.append({'ref':item_ref})
            set_list[k]['items'] = items
        return set_list


    def _populate_set_item_info(self, set_list):

        # keys are refs to items, values are a ref to one of the
        # sets that they are in.  We build a lookup here first so that
        # we don't duplicate items in the ws call, but depending
        # on the set composition it may be cheaper to omit this
        # check and build the objects call directly with duplicates
        item_refs = {}
        for s in set_list:
            for i in s['items']:
                item_refs[i['ref']] = s['ref']

        objects = []
        for ref in item_refs:
            objects.append({
                    'ref': item_refs[ref],
                    'obj_ref_path': [ref]
                })

        obj_info_list = self.ws.get_object_info_new({
                                    'objects':objects,
                                    'includeMetadata':1
                                })

        # build info lookup
        item_info = {}
        for o in obj_info_list:
            item_info[self._build_obj_ref(o)] = o

        for s in set_list:
            for item in s['items']:
                if item['ref'] in item_info:
                    item['info'] = item_info[item['ref']]

        return set_list



    def _build_obj_ref(self, obj_info):
        return str(obj_info[6]) + '/' + str(obj_info[0]) + '/' + str(obj_info[4])


    def get_set_items(self, params):
        

        return {}


    # def _check_save_set_params(self, params):
    #     if 'data' not in params:
    #         raise ValueError('"data" parameter field specifiying the set is required')
    #     if 'workspace_id' not in params and 'workspace_name' not in params:
    #         raise ValueError('"workspace_id" or "workspace_name" parameter fields specifiying the workspace is required')
    #     if 'output_object_name' not in params:
    #         raise ValueError('"output_object_name" parameter field is required')


    # def _build_ws_save_obj_params(self, set_type, provenance, params):

    #     save_params = {
    #         'objects': [{
    #             'name': params['output_object_name'],
    #             'data': params['data'],
    #             'type': set_type,
    #             'provenance': provenance,
    #             'hidden': 0
    #         }]
    #     }

    #     if 'workspace_name' in params:
    #         save_params['workspace'] = params['workspace_name']
    #     else:
    #         save_params['id'] = params['workspace_id']

    #     return save_params



    # def get_set(self, ref, include_item_info=False, ref_path_to_set=[]):
    #     '''
    #     Get a set object from the Workspace using the set_type provided (e.g. set_type=KBaseSets.ReadsSet)
    #     '''
    #     ws_data = self._get_set_from_ws(ref, ref_path_to_set)

    #     if include_item_info:
    #         self._populate_item_object_info(ws_data, ref_path_to_set)

    #     return ws_data
    


    # def _get_set_from_ws(self, ref, ref_path_to_set):

    #     # typedef structure {
    #     #     list<ObjectSpecification> objects;
    #     #     boolean ignoreErrors;
    #     #     boolean no_data;
    #     # } GetObjects2Params;
    #     selector = self._build_ws_obj_selector(ref, ref_path_to_set)
    #     ws_data = self.ws.get_objects2({'objects': [selector] })

    #     data = ws_data['data'][0]['data']
    #     info = ws_data['data'][0]['info']

    #     return { 'data': data, 'info': info }



    # def _populate_item_object_info(self, set, ref_path_to_set):

    #     info = set['info']
    #     items = set['data']['items']
    #     set_ref = str(info[6]) + '/' + str(info[0]) + '/' + str(info[4])
    #     ref_path_to_item = ref_path_to_set + [set_ref]

    #     objects = []
    #     for item in items:
    #         objects.append(
    #             self._build_ws_obj_selector(item['ref'], ref_path_to_item))

    #     obj_info_list = self.ws.get_object_info_new({
    #                                 'objects': objects,
    #                                 'includeMetadata': 1 })

    #     for k in range(0, len(obj_info_list)):
    #         items[k]['info'] = obj_info_list[k]


    # def _build_ws_obj_selector(self, ref, ref_path_to_set):
    #     if ref_path_to_set and len(ref_path_to_set)>0:
    #         obj_ref_path = []
    #         for r in ref_path_to_set[1:]:
    #             obj_ref_path.append(r)
    #         obj_ref_path.append(ref)
    #         return {
    #             'ref': ref_path_to_set[0],
    #             'obj_ref_path':obj_ref_path
    #         }
    #     return { 'ref': ref } 

