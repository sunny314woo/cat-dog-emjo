"""Keep opaque clothing inside a segmented silhouette, with soft outer edges."""
def repair_foreground_alpha(image,source=None):
    import numpy as np
    from scipy.ndimage import binary_fill_holes, binary_erosion
    from PIL import Image
    image=image.convert('RGBA')
    alpha=np.asarray(image.getchannel('A')).copy()
    silhouette=binary_fill_holes(alpha>=64)
    interior=binary_erosion(silhouette,iterations=2,border_value=0)
    alpha[interior]=255
    alpha[alpha<32]=0
    output=source.convert('RGBA') if source is not None else image
    output.putalpha(Image.fromarray(alpha))
    return output
