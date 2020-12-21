plugins = []
try:
    from . import about_dot_com_plugin
    plugins.append(about_dot_com_plugin.AboutDotComPlugin)
except ImportError:
    pass
try:
    from . import foodnetwork_plugin
    plugins.append(foodnetwork_plugin.FoodNetworkPlugin)
except ImportError:
    pass
try:
    from . import allrecipes_plugin
    plugins.append(allrecipes_plugin.AllRecipesPlugin)
except ImportError:
    pass
try:
    from . import ica_se_plugin
    plugins.append(ica_se_plugin.IcaSePlugin)
except ImportError:
    pass
try:
    from . import epicurious_plugin
    plugins.append(epicurious_plugin.EpicuriousPlugin)
except ImportError:
    pass
try:
    from . import nytimes_plugin
    plugins.append(nytimes_plugin.NYTPlugin)
except ImportError:
    pass
try:
    from . import cooksillustrated_plugin
    plugins.append(cooksillustrated_plugin.WebImporterPlugin)
    plugins.append(cooksillustrated_plugin.CooksIllustratedPlugin)
except ImportError:
    pass
try:
    from . import chefkoch_de_plugin
    plugins.append(chefkoch_de_plugin.ChefkochDePlugin)
except ImportError:
    pass
try:
    from . import thermomix_plugin
    plugins.append(thermomix_plugin.ThermomixPlugin)
except ImportError:
    pass
