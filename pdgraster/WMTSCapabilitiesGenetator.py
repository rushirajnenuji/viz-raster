import xml.etree.ElementTree as ET
from xml.dom import minidom

class WMTSCapabilitiesGenerator:
    """
    A class to generate WMTS Capabilities XML for a given dataset.

    title: str = "PDG Ice-wedge polygon high"
    base_url: str = "https://arcticdata.io/data/tiles"
    doi: str = "10.18739/A2KW57K57"
    layer_title: str = "iwp_high"
    layer_identifier: str = "iwp_high"
    bounding_box: dict = {
    "left": -179.91531896747117,
    "right": 179.91531896747247,
    "bottom": 50.16996707215903,
    "top": 80.0978646943821 },
    tile_format: str = "image/png"
    tile_matrix_set: str = "WGS1984Quad"
    scale_denominator_base: float = 279541132.0143589
    tile_width: int = 256
    tile_height: int = 256
    max_z_level: int = 15
    resource_template: str = "{base_url}/{doi}/{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.png"
    supported_crs: str = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    well_known_scale_set: str = "http://www.opengis.net/def/wkss/OGC/1.0/GoogleCRS84Quad"



    """

    def __init__(self, title, base_url, doi, layer_title, layer_identifier, bounding_box,
                 tile_format, tile_matrix_set, scale_denominator_base,
                 tile_width, tile_height, max_z_level, resource_template, supported_crs,
                 well_known_scale_set):
        

        self.title = title
        self.base_url = base_url
        self.doi = doi
        self.capabilities_url = f"{base_url}/{doi}/WMTSCapabilities.xml"
        self.tiles_url = f"{base_url}/{doi}/"
        self.layer_title = layer_title
        self.layer_identifier = layer_identifier
        self.bounding_box = bounding_box
        self.tile_format = tile_format
        self.tile_matrix_set = tile_matrix_set
        self.scale_denominator_base = scale_denominator_base
        self.top_left_corner = f"{bounding_box['left']} {bounding_box['top']}"
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.max_z_level = max_z_level
        self.resource_template = resource_template

        # TBD: Check is these are needed
        self.supported_crs = supported_crs
        self.well_known_scale_set = well_known_scale_set

    def generate_capabilities(self):
        """
        Generates the WMTS Capabilities XML as a string.
        """
        # Root element
        root = ET.Element("Capabilities", attrib={
            "xmlns": "http://www.opengis.net/wmts/1.0",
            "xmlns:ows": "http://www.opengis.net/ows/1.1",
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:gml": "http://www.opengis.net/gml",
            "xsi:schemaLocation": "http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd",
            "version": "1.0.0"
        })

        self._add_service_identification(root)
        self._add_operations_metadata(root)
        self._add_contents(root)
        ET.SubElement(root, "ServiceMetadataURL", attrib={"xlink:href": self.capabilities_url})

        # Pretty print XML
        xml_str = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xml_str)
        return parsed.toprettyxml(indent="  ")

    def _add_service_identification(self, root):
        service_identification = ET.SubElement(root, "ows:ServiceIdentification")
        ET.SubElement(service_identification, "ows:Title").text = self.title
        ET.SubElement(service_identification, "ows:ServiceType").text = "OGC WMTS"
        ET.SubElement(service_identification, "ows:ServiceTypeVersion").text = "1.0.0"

    def _add_operations_metadata(self, root):
        operations_metadata = ET.SubElement(root, "ows:OperationsMetadata")
        self._add_operation(operations_metadata, "GetCapabilities", self.capabilities_url)
        self._add_operation(operations_metadata, "GetTile", self.tiles_url)

    def _add_operation(self, parent, name, href):
        operation = ET.SubElement(parent, "ows:Operation", attrib={"name": name})
        dcp = ET.SubElement(operation, "ows:DCP")
        http = ET.SubElement(dcp, "ows:HTTP")
        get = ET.SubElement(http, "ows:Get", attrib={"xlink:href": href})
        constraint = ET.SubElement(get, "ows:Constraint", attrib={"name": "GetEncoding"})
        allowed_values = ET.SubElement(constraint, "ows:AllowedValues")
        ET.SubElement(allowed_values, "ows:Value").text = "RESTful"

    def _add_contents(self, root):
        contents = ET.SubElement(root, "Contents")
        layer = ET.SubElement(contents, "Layer")
        ET.SubElement(layer, "ows:Title").text = "iwp_high"
        ET.SubElement(layer, "ows:Identifier").text = "iwp_high"

        wgs84_bbox = ET.SubElement(layer, "ows:WGS84BoundingBox")
        ET.SubElement(wgs84_bbox, "ows:LowerCorner").text = f"{self.bounding_box['left']} {self.bounding_box['bottom']}"
        ET.SubElement(wgs84_bbox, "ows:UpperCorner").text = f"{self.bounding_box['right']} {self.bounding_box['top']}"


        style = ET.SubElement(layer, "Style", attrib={"isDefault": "true"})
        ET.SubElement(style, "ows:Title").text = "Default Style"
        ET.SubElement(style, "ows:Identifier").text = "default"

        ET.SubElement(layer, "Format").text = "image/png"
        tile_matrix_set_link = ET.SubElement(layer, "TileMatrixSetLink")
        ET.SubElement(tile_matrix_set_link, "TileMatrixSet").text = "WGS1984Quad"

        resource_url = ET.SubElement(layer, "ResourceURL", attrib={
            "format": "image/png",
            "resourceType": "tile",
            "template": f"{self.tiles_url}{{TileMatrixSet}}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}.png"
        })

        self._add_tile_matrix_set(contents)

    def _add_tile_matrix_set(self, contents):
        tile_matrix_set = ET.SubElement(contents, "TileMatrixSet", attrib={"xml:id": "WorldCRS84Quad"})
        ET.SubElement(tile_matrix_set, "ows:Title").text = "CRS84 for the World"
        ET.SubElement(tile_matrix_set, "ows:Identifier").text = "WGS1984Quad"

        bounding_box = ET.SubElement(tile_matrix_set, "ows:BoundingBox", attrib={"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"})
        ET.SubElement(bounding_box, "ows:LowerCorner").text = "-180 -90"
        ET.SubElement(bounding_box, "ows:UpperCorner").text = "180 90"

        ET.SubElement(tile_matrix_set, "ows:SupportedCRS").text = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
        ET.SubElement(tile_matrix_set, "WellKnownScaleSet").text = "http://www.opengis.net/def/wkss/OGC/1.0/GoogleCRS84Quad"

        for i in range(self.max_z_level + 1):  # Generate levels from 0 to max_z_level
            tile_matrix = ET.SubElement(tile_matrix_set, "TileMatrix")
            ET.SubElement(tile_matrix, "ows:Identifier").text = str(i)
            ET.SubElement(tile_matrix, "ScaleDenominator").text = str(self.scale_denominator_base / (2 ** i))
            ET.SubElement(tile_matrix, "TopLeftCorner").text = self.top_left_corner
            ET.SubElement(tile_matrix, "TileWidth").text = str(self.tile_width)
            ET.SubElement(tile_matrix, "TileHeight").text = str(self.tile_height)
            ET.SubElement(tile_matrix, "MatrixWidth").text = str(2 ** (i+1))
            ET.SubElement(tile_matrix, "MatrixHeight").text = str(2 ** i)

# For testing purposes. Remove after

if __name__ == "__main__":
    # Parameters for the generator
    title = "PDG Ice-wedge polygon high"
    base_url = "https://arcticdata.io/data/tiles"
    doi = "10.18739/A2KW57K57"
    layer_title = "iwp_high"
    layer_identifier = "iwp_high"
    bounding_box = {
    "left": -179.91531896747117,
    "right": 179.91531896747247,
    "bottom": 50.16996707215903,
    "top": 80.0978646943821
}
    tile_format = "image/png"
    tile_matrix_set = "WGS1984Quad"
    scale_denominator_base = 279541132.0143589
    top_left_corner = "-180 90"
    tile_width = 256
    tile_height = 256
    max_z_level = 15
    resource_template = "{base_url}/{doi}/{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.png"
    supported_crs = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    well_known_scale_set = "http://www.opengis.net/def/wkss/OGC/1.0/GoogleCRS84Quad"

    # TBD: remove after the testing is completed
    # Instantiate the generator
    generator = WMTSCapabilitiesGenerator(
        title=title,
        base_url=base_url,
        doi=doi,
        layer_title=layer_title,
        layer_identifier=layer_identifier,
        bounding_box=bounding_box,
        tile_format=tile_format,
        tile_matrix_set=tile_matrix_set,
        scale_denominator_base=scale_denominator_base,
        tile_width=tile_width,
        tile_height=tile_height,
        max_z_level=max_z_level,
        resource_template=resource_template,
        supported_crs=supported_crs,
        well_known_scale_set=well_known_scale_set
    )

    # Generate the WMTS Capabilities XML
    wmts_xml = generator.generate_capabilities()

    # Write the XML to a file
    with open("WMTSCapabilities.xml", "w") as f:
        f.write(wmts_xml)

    print("WMTS Capabilities document generated successfully!")
