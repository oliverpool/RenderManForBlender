from ..rman_render import RmanRender
from ..icons import icons
from .rman_ui_base import _RManPanelHeader
import bpy

class PRMAN_PT_Renderman_UI_Panel(bpy.types.Panel, _RManPanelHeader):
    '''Adds a RenderMan panel to the RenderMan VIEW_3D side tab
    '''

    bl_label = "RenderMan"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Renderman"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman

        # save Scene
        # layout.operator("wm.save_mainfile", text="Save Scene", icon='FILE_TICK')

        # layout.separator()

        if context.scene.render.engine != "PRMAN_RENDER":
            return

        # Render
        rman_render = RmanRender.get_rman_render()
        is_rman_interactive_running = rman_render.rman_interactive_running        

        if not is_rman_interactive_running:

            row = layout.row(align=True)
            rman_render_icon = icons.get_icon("rman_render")
            row.operator("render.render", text="Render",
                        icon_value=rman_render_icon.icon_id)

            row.prop(context.scene, "rm_render", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render else 'DISCLOSURE_TRI_RIGHT')

            if context.scene.rm_render:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # Display Driver
                row.prop(rm, "render_into")

                row = box.row(align=True)
                row.prop(rm, "do_holdout_matte", text="Render Holdouts")
                
                # animation
                row = box.row(align=True)
                rman_batch = icons.get_icon("rman_batch")
                row.operator("render.render", text="Render Animation",
                            icon_value=rman_batch.icon_id).animation = True

            row = layout.row(align=True)
            rman_batch = icons.get_icon("rman_batch")

            row.operator("renderman.external_render",
                        text="External Render", icon_value=rman_batch.icon_id)

            row.prop(context.scene, "rm_render_external", text="",
                    icon='DISCLOSURE_TRI_DOWN' if context.scene.rm_render_external else 'DISCLOSURE_TRI_RIGHT')
            if context.scene.rm_render_external:
                scene = context.scene
                rd = scene.render

                box = layout.box()
                row = box.row(align=True)

                # animation
                row = box.row(align=True)
                row.prop(rm, "external_animation")

                row = box.row(align=True)
                row.enabled = rm.external_animation
                row.prop(scene, "frame_start", text="Start")
                row.prop(scene, "frame_end", text="End")

                # spool render
                row = box.row(align=True)
                col = row.column()
                col.prop(rm, "queuing_system", text='')            

        else:
            row = layout.row(align=True)
            rman_rerender_controls = icons.get_icon("rman_ipr_cancel")
            row.operator('lighting.stop_interactive', text="Stop IPR",
                            icon_value=rman_rerender_controls.icon_id)            

        layout.separator()

        # Create Camera
        row = layout.row(align=True)
        row.operator("object.add_prm_camera",
                     text="Add Camera", icon='CAMERA_DATA')

        row.prop(context.scene, "prm_cam", text="",
                 icon='DISCLOSURE_TRI_DOWN' if context.scene.prm_cam else 'DISCLOSURE_TRI_RIGHT')

        if context.scene.prm_cam:
            ob = bpy.context.object
            box = layout.box()
            row = box.row(align=True)
            row.menu("PRMAN_MT_Camera_List_Menu",
                     text="Camera List", icon='CAMERA_DATA')

            if ob.type == 'CAMERA':

                row = box.row(align=True)
                row.prop(ob, "name", text="", icon='LIGHT_HEMI')
                row.prop(ob, "hide_viewport", text="")
                row.prop(ob, "hide_render",
                         icon='RESTRICT_RENDER_OFF', text="")
                row.operator("object.delete_cameras",
                             text="", icon='PANEL_CLOSE')

                row = box.row(align=True)
                row.scale_x = 2
                row.operator("view3d.object_as_camera", text="", icon='CURSOR')

                row.scale_x = 2
                row.operator("view3d.view_camera", text="", icon='HIDE_OFF')

                if context.space_data.lock_camera == False:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='UNLOCKED').data_path = "space_data.lock_camera"
                elif context.space_data.lock_camera == True:
                    row.scale_x = 2
                    row.operator("wm.context_toggle", text="",
                                 icon='LOCKED').data_path = "space_data.lock_camera"

                row.scale_x = 2
                row.operator("view3d.camera_to_view",
                             text="", icon='VIEW3D')

                row = box.row(align=True)
                row.label(text="Depth Of Field :")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_object", text="")
                #row.prop(context.object.data.cycles, "aperture_type", text="")

                row = box.row(align=True)
                row.prop(context.object.data.dof, "focus_distance", text="Distance")

            else:
                row = layout.row(align=True)
                row.label(text="No Camera Selected")

        layout.separator()
        layout.label(text="Lights:")
        box = layout.box()

        box.menu('VIEW3D_MT_RM_Add_Light_Menu', text='Add Light', icon_value=bpy.types.VIEW3D_MT_RM_Add_Light_Menu.get_icon_id())
        box.menu('VIEW3D_MT_RM_Add_LightFilter_Menu', text='Add Light Filter', icon_value=bpy.types.VIEW3D_MT_RM_Add_LightFilter_Menu.get_icon_id())               

        layout.separator()
        layout.label(text="Apps:")
        box = layout.box()
        rman_it = icons.get_icon("rman_it")
        box.operator("rman.start_it", icon_value=rman_it.icon_id)  
        rman_lq = icons.get_icon("rman_localqueue")
        box.operator("rman.start_localqueue", icon_value=rman_lq.icon_id)          
        
        selected_objects = []
        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type not in ['CAMERA', 'LIGHT', 'SPEAKER']:
                    selected_objects.append(obj)

        if selected_objects:
            layout.separator()
            layout.label(text="Seleced Objects:")
            box = layout.box()

            # Add Bxdf                 
            box.menu('VIEW3D_MT_RM_Add_bxdf_Menu', text='Add New Material', icon_value=bpy.types.VIEW3D_MT_RM_Add_bxdf_Menu.get_icon_id())                 

            # Make Selected Geo Emissive
            rman_meshlight = icons.get_icon("out_PxrMeshLight")
            box.operator("object.rman_create_meshlight", text="Convert to Mesh Light",
                         icon_value=rman_meshlight.icon_id)

            # Add Subdiv Sheme
            rman_subdiv = icons.get_icon("rman_subdiv")
            box.operator("object.rman_add_subdiv_scheme",
                         text="Convert to Subdiv", icon_value=rman_subdiv.icon_id)

            # Add/Create RIB Box /
            # Create Archive node
            box.menu('VIEW3D_MT_RM_Add_Export_Menu', icon_value=bpy.types.VIEW3D_MT_RM_Add_Export_Menu.get_icon_id())

        # Diagnose
        layout.separator()
        layout.label(text='Diagnose')
        box = layout.box()
        box.enabled = not is_rman_interactive_running
        rman_rib = icons.get_icon('rman_rib_small')
        box.operator("rman.open_scene_rib", text='View RIB', icon_value=rman_rib.icon_id)
        if selected_objects:
            box.operator("rman.open_selected_rib", text='View Selected RIB', icon_value=rman_rib.icon_id)



        layout.separator()
        # RenderMan Doc
        rman_help = icons.get_icon("rman_help")
        layout.operator("wm.url_open", text="RenderMan Docs",
                        icon_value=rman_help.icon_id).url = "https://github.com/prman-pixar/RenderManForBlender/wiki/Documentation-Home"
        rman_info = icons.get_icon("rman_blender")
        layout.operator("wm.url_open", text="About RenderMan",
                        icon_value=rman_info.icon_id).url = "https://renderman.pixar.com/store/intro"

        # Enable the menu item to display the examples menu in the RenderMan
        # Panel.
        layout.separator()
        rman_beaker = icons.get_icon("rman_beaker")
        layout.menu("PRMAN_MT_LoadExampleSceneMenu", icon_value=rman_beaker.icon_id)    

classes = [
    PRMAN_PT_Renderman_UI_Panel,

]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            rfb_log().debug('Could not unregister class: %s' % str(cls))
            pass       