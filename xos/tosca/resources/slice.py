import os
import pdb
import sys
import tempfile
sys.path.append("/opt/tosca")
from translator.toscalib.tosca_template import ToscaTemplate

from core.models import Slice,User,Site,Network,NetworkSlice,SliceRole,SlicePrivilege,Service

from xosresource import XOSResource

class XOSSlice(XOSResource):
    provides = "tosca.nodes.Slice"
    xos_model = Slice
    copyin_props = ["enabled", "description", "slice_url", "max_instances", "default_isolation"]

    def get_xos_args(self):
        args = super(XOSSlice, self).get_xos_args()

        site_name = self.get_requirement("tosca.relationships.MemberOfSite", throw_exception=True)
        site = self.get_xos_object(Site, login_base=site_name)
        args["site"] = site

        serviceName = self.get_requirement("tosca.relationships.MemberOfService", throw_exception=False)
        if serviceName:
            service = self.get_xos_object(Service, name=serviceName)
            args["service"] = service

        return args

    def postprocess(self, obj):
        for net_name in self.get_requirements("tosca.relationships.ConnectsToNetwork"):
            net = self.get_xos_object(Network, name=net_name)
            if not NetworkSlice.objects.filter(network=net, slice=obj):
                ns = NetworkSlice(network=net, slice=obj)
                ns.save()
                self.info("Added network connection from '%s' to '%s'" % (str(obj), str(net)))

        rolemap = ( ("tosca.relationships.AdminPrivilege", "admin"), ("tosca.relationships.AccessPrivilege", "access"),
                    ("tosca.relationships.PIPrivilege", "pi"), ("tosca.relationships.TechPrivilege", "tech") )
        self.postprocess_privileges(SliceRole, SlicePrivilege, rolemap, obj, "slice")

    def create(self):
        nodetemplate = self.nodetemplate
        sliceName = nodetemplate.name

        xos_args = self.get_xos_args()
        slice = Slice(**xos_args)
        slice.caller = self.user
        slice.save()

        self.postprocess(slice)

        self.info("Created Slice '%s' on Site '%s'" % (str(slice), str(slice.site)))

    def delete(self, obj):
        if obj.instances.exists():
            self.info("Slice %s has active instances; skipping delete" % obj.name)
            return
        super(XOSSlice, self).delete(obj)



