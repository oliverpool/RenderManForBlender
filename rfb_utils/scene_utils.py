from . import shadergraph_utils
from . import object_utils
from . import prefs_utils
from ..rfb_logger import rfb_log
import bpy
import sys


# ------------- Atom's helper functions -------------
GLOBAL_ZERO_PADDING = 5
# Objects that can be exported as a polymesh via Blender to_mesh() method.
# ['MESH','CURVE','FONT']
SUPPORTED_INSTANCE_TYPES = ['MESH', 'CURVE', 'FONT', 'SURFACE']
SUPPORTED_DUPLI_TYPES = ['FACES', 'VERTS', 'GROUP']    # Supported dupli types.
# These object types can have materials.
MATERIAL_TYPES = ['MESH', 'CURVE', 'FONT']
# Objects without to_mesh() conversion capabilities.
EXCLUDED_OBJECT_TYPES = ['LIGHT', 'CAMERA', 'ARMATURE']
# Only these light types affect volumes.
VOLUMETRIC_LIGHT_TYPES = ['SPOT', 'AREA', 'POINT']
MATERIAL_PREFIX = "mat_"
TEXTURE_PREFIX = "tex_"
MESH_PREFIX = "me_"
CURVE_PREFIX = "cu_"
GROUP_PREFIX = "group_"
MESHLIGHT_PREFIX = "meshlight_"
PSYS_PREFIX = "psys_"
DUPLI_PREFIX = "dupli_"
DUPLI_SOURCE_PREFIX = "dup_src_"

RMAN_VOL_TYPES = ['RI_VOLUME', 'OPENVDB', 'FLUID']

# ------------- Filtering -------------
def is_visible_layer(scene, ob):
    #
    #FIXME for i in range(len(scene.layers)):
    #    if scene.layers[i] and ob.layers[i]:
    #        return True
    return True

def get_renderman_layer(context):
    rm_rl = None
    layer = context.view_layer  
    rm_rl = layer.renderman 

    return rm_rl    

def any_areas_shading():           
    '''
    Loop through all of the windows/areas and return True if any of
    the view_3d areas have their shading set to RENDERED. Otherwise,
    return False.
    '''    
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D' and space.shading.type == 'RENDERED':
                        return True
    return False           

def get_render_variant(bl_scene):
    #if bl_scene.renderman.is_ncr_license and bl_scene.renderman.renderVariant != 'prman':
    if not bl_scene.renderman.has_xpu_license and bl_scene.renderman.renderVariant != 'prman':
        rfb_log().warning("Your RenderMan license does not include XPU. Reverting to RIS.")
        return 'prman'

    if sys.platform == ("darwin") and bl_scene.renderman.renderVariant != 'prman':
        rfb_log().warning("XPU is not implemented on OSX: using RIS...")
        return 'prman'

    return bl_scene.renderman.renderVariant    

def set_render_variant_config(bl_scene, config, render_config):
    variant = get_render_variant(bl_scene)
    if variant.startswith('xpu'):
        variant = 'xpu'
    config.SetString('rendervariant', variant)

    if variant == 'xpu':

        '''
        ## TODO: For when XPU can support multiple gpu devices...

        xpu_gpu_devices = prefs_utils.get_pref('rman_xpu_gpu_devices')
        gpus = list()
        for device in xpu_gpu_devices:
            if device.use:
                gpus.append(device.id)
        if gpus:
            render_config.SetIntegerArray('xpu:gpuconfig', gpus, len(gpus))    

        # For now, there is only one CPU
        xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
        device = xpu_cpu_devices[0]

        render_config.SetInteger('xpu:cpuconfig', int(device.use))

        if not gpus and not device.use:
            # Nothing was selected, we should at least use the cpu.
            print("No devices were selected for XPU. Defaulting to CPU.")
            render_config.SetInteger('xpu:cpuconfig', 1)
        '''

        # Else, we only support selecting one GPU
        xpu_gpu_device = int(prefs_utils.get_pref('rman_xpu_gpu_selection'))
        if xpu_gpu_device > -1:
            render_config.SetIntegerArray('xpu:gpuconfig', [xpu_gpu_device], 1)

        # For now, there is only one CPU
        xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
        if len(xpu_cpu_devices) > 0:
            device = xpu_cpu_devices[0]
            render_config.SetInteger('xpu:cpuconfig', int(device.use))    

            if xpu_gpu_device == -1 and not device.use:
                # Nothing was selected, we should at least use the cpu.
                print("No devices were selected for XPU. Defaulting to CPU.")
                render_config.SetInteger('xpu:cpuconfig', 1)                         
        else:
            render_config.SetInteger('xpu:cpuconfig', 1)         

def set_render_variant_spool(bl_scene, args, is_tractor=False):
    variant = get_render_variant(bl_scene)
    if variant.startswith('xpu'):
        variant = 'xpu'
    args.append('-variant')
    args.append(variant)

    if variant == 'xpu':
        device_list = list()
        if not is_tractor:
            '''
            ## TODO: For when XPU can support multiple gpu devices...
            xpu_gpu_devices = prefs_utils.get_pref('rman_xpu_gpu_devices')
            for device in xpu_gpu_devices:
                if device.use:
                    device_list.append('gpu%d' % device.id)

            xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
            device = xpu_cpu_devices[0]

            if device.use or not device_list:
                device_list.append('cpu')
            '''
            xpu_gpu_device = int(prefs_utils.get_pref('rman_xpu_gpu_selection'))
            if xpu_gpu_device > -1:
                device_list.append('gpu%d' % xpu_gpu_device)

            xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
            if len(xpu_cpu_devices) > 0:
                device = xpu_cpu_devices[0]

                if device.use or xpu_gpu_device < 0:
                    device_list.append('cpu')            
            else:
                device_list.append('cpu')      

        else:
            # Don't add the gpu list if we are spooling to Tractor
            # There is no way for us to know what is available on the blade,
            # so just ask for CPU for now.
            device_list.append('cpu')

        if device_list:
            device_list = ','.join(device_list)
            args.append('-xpudevices:%s' % device_list)  

def get_all_portals(light_ob):
    """Return a list of portals

    Args:
    light_ob (bpy.types.Object) - light object

    Returns:
    (list) - list of portals attached to this light
    """    

    portals = list()
    if light_ob.type != 'LIGHT':
        return portals

    light = light_ob.data
    rm = light.renderman  
    light_shader = rm.get_light_node()

    if light_shader:
        light_shader_name = rm.get_light_node_name()

        if light_shader_name == 'PxrDomeLight':
            for portal_pointer in rm.portal_lights:
                if portal_pointer.linked_portal_ob:
                    portals.append(portal_pointer.linked_portal_ob)
                 
    return portals

def get_all_volume_objects(scene):
    """Return a list of volume objects in the scene

    Args:
    scene (byp.types.Scene) - scene file to look for lights

    Returns:
    (list) - volume objects
    """    
    global RMAN_VOL_TYPES
    volumes = list()
    for ob in scene.objects:
        if object_utils._detect_primitive_(ob) in RMAN_VOL_TYPES:
            volumes.append(ob)
    return volumes

def get_light_group(light_ob, scene):
    """Return the name of the lightGroup for this
    light, if any

    Args:
    light_ob (bpy.types.Object) - object we are interested in
    scene (byp.types.Scene) - scene file to look for lights

    Returns:
    (str) - light group name
    """

    scene_rm = scene.renderman
    for lg in scene_rm.light_groups:
        for member in lg.members:
            if light_ob == member.light_ob:
                return lg.name
    return ''         

def get_all_lights(scene, include_light_filters=True):
    """Return a list of all lights in the scene, including
    mesh lights

    Args:
    scene (byp.types.Scene) - scene file to look for lights
    include_light_filters (bool) - whether or not light filters should be included in the list

    Returns:
    (list) - list of all lights
    """

    lights = list()
    for ob in scene.objects:
        if ob.type == 'LIGHT':
            if hasattr(ob.data, 'renderman'):
                if include_light_filters:
                    lights.append(ob)
                elif ob.data.renderman.renderman_light_role == 'RMAN_LIGHT':            
                    lights.append(ob)
        else:
            mat = getattr(ob, 'active_material', None)
            if not mat:
                continue
            output = shadergraph_utils.is_renderman_nodetree(mat)
            if not output:
                continue
            if len(output.inputs) > 1:
                socket = output.inputs[1]
                if socket.is_linked:
                    node = socket.links[0].from_node
                    if node.bl_label == 'PxrMeshLight':
                        lights.append(ob)       
    return lights

def get_all_lightfilters(scene):
    """Return a list of all lightfilters in the scene

    Args:
    scene (byp.types.Scene) - scene file to look for lights
    
    Returns:
    (list) - list of all lightfilters
    """

    lightfilters = list()
    for ob in scene.objects:
        if ob.type == 'LIGHT':
            if hasattr(ob.data, 'renderman'):
                if ob.data.renderman.renderman_light_role == 'RMAN_LIGHTFILTER':            
                    lightfilters.append(ob)

    return lightfilters    

def get_light_groups_in_scene(scene):
    """ Return a dictionary of light groups in the scene

    Args:
    scene (byp.types.Scene) - scene file to look for lights

    Returns:
    (dict) - dictionary of light gropus to lights
    """

    lgt_grps = dict()
    for light in get_all_lights(scene, include_light_filters=False):
        light_shader = shadergraph_utils.get_light_node(light, include_light_filters=False)
        lgt_grp_nm = getattr(light_shader, 'lightGroup', '')
        if lgt_grp_nm:
            lights_list = lgt_grps.get(lgt_grp_nm, list())
            lights_list.append(light)
            lgt_grps[lgt_grp_nm] = lights_list

    return lgt_grps

def find_node_owner(node, context=None):
    """ Return the owner of this node

    Args:
    node (bpy.types.ShaderNode) - the node that the caller is trying to find its owner
    context (bpy.types.Context) - Blender context

    Returns:
    (id_data) - The owner of this node
    """    
    nt = node.id_data

    def check_group(group_node, nt):
        node_tree = getattr(group_node, 'node_tree', None)
        if node_tree is None:
            return False          
        if node_tree == nt:
            return node_tree

        for n in group_node.node_tree.nodes:
            if n.bl_idname == 'ShaderNodeGroup':
                if check_group(n, nt):
                    return True
        return False
            
    for mat in bpy.data.materials:
        if mat.node_tree is None:
            continue
        if mat.node_tree == nt:
            return mat
        for n in mat.node_tree.nodes:
            # check if the node belongs to a group node
            node_tree = getattr(n, 'node_tree', None)
            if node_tree is None:
                continue            
            if check_group(n, nt):
                return mat

    for world in bpy.data.worlds:
        if world.node_tree == nt:
            return world

    for ob in bpy.data.objects:
        if ob.type == 'LIGHT':
            light = ob.data
            if light.node_tree == nt:
                return ob
        elif ob.type == 'CAMERA':
            if shadergraph_utils.find_projection_node(ob) == node:
                return ob
    return None

def find_node_by_name(node_name, ob_name):
    """ Finder shader node and object by name(s)

    Args:
    node_name (str) - name of the node we are trying to find
    ob_name (str) - object name we are trying to look for that has node_name

    Returns:
    (list) - node and object
    """    

    group_node = bpy.data.node_groups.get(ob_name)
    if group_node:
        node = group_node.nodes.get(node_name, None) 
        if node:
            return (node, group_node)

    mat = bpy.data.materials.get(ob_name, None)
    if mat:
        node = mat.node_tree.nodes.get(node_name, None)
        if node:
            return (node, mat)

    world = bpy.data.worlds.get(ob_name, None)
    if world:
        node = world.node_tree.nodes.get(node_name, None)
        if node:
            return (node, world)

    obj = bpy.data.objects.get(ob_name, None)
    if obj:
        rman_type = object_utils._detect_primitive_(obj)
        if rman_type in ['LIGHT', 'LIGHTFILTER']:
            light_node = shadergraph_utils.get_light_node(obj, include_light_filters=True)
            return (light_node, obj)
        elif rman_type == 'CAMERA':
            node = shadergraph_utils.find_projection_node(obj)
            if node:
                return (node, obj)

    return (None, None)

def is_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render) or \
        (ob.type in ['ARMATURE', 'LATTICE', 'EMPTY'] and ob.instance_type not in SUPPORTED_DUPLI_TYPES)
    # and not ob.type in ('CAMERA', 'ARMATURE', 'LATTICE'))


def is_renderable_or_parent(scene, ob):
    if ob.type == 'CAMERA':
        return True
    if is_renderable(scene, ob):
        return True
    elif hasattr(ob, 'children') and ob.children:
        for child in ob.children:
            if is_renderable_or_parent(scene, child):
                return True
    return False


def is_data_renderable(scene, ob):
    return (is_visible_layer(scene, ob) and not ob.hide_render and ob.type not in ('EMPTY', 'ARMATURE', 'LATTICE'))


def renderable_objects(scene):
    return [ob for ob in scene.objects if (is_renderable(scene, ob) or is_data_renderable(scene, ob))]

def _get_subframes_(segs, scene):
    if segs == 0:
        return []
    min = -1.0
    rm = scene.renderman
    shutter_interval = rm.shutter_angle / 360.0
    if rm.shutter_timing == 'FRAME_CENTER':
        min = 0 - .5 * shutter_interval
    elif rm.shutter_timing == 'FRAME_CLOSE':
        min = 0 - shutter_interval
    elif rm.shutter_timing == 'FRAME_OPEN':
        min = 0

    return [min + i * shutter_interval / (segs - 1) for i in range(segs)]