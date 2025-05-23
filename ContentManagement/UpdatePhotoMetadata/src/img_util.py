from PIL import Image, ExifTags

class ImageUtil:

    def __init__(self):
        pass

    def get_exif_details(self, jpg_stream):
        # Source: https://stackoverflow.com/a/77539176
        IFD_CODE_LOOKUP = {i.value: i.name for i in ExifTags.IFD}

        with Image.open(jpg_stream) as img:

            img_exif = img.getexif()
            print(img_exif)

            for tag_code, value in img_exif.items():

                # if the tag is an IFD block, nest into it
                if tag_code in IFD_CODE_LOOKUP:

                    ifd_tag_name = IFD_CODE_LOOKUP[tag_code]
                    print(f"IFD '{ifd_tag_name}' (code {tag_code}):")
                    ifd_data = img_exif.get_ifd(tag_code).items()

                    for nested_key, nested_value in ifd_data:
                        nested_tag_name = ExifTags.GPSTAGS.get(nested_key, None) or ExifTags.TAGS.get(nested_key, None) or nested_key
                        print(f"  {nested_tag_name}: {nested_value}")

                else:
                    # root-level tag
                    print(f"{ExifTags.TAGS.get(tag_code)}: {value}")

    def get_lightroom_keywords(self, jpg_stream):
        with Image.open(jpg_stream) as img:
            img_xmp = img.getxmp()
            keyword_list = img_xmp['xmpmeta']['RDF']['Description']['subject']['Bag']['li']
            return keyword_list
