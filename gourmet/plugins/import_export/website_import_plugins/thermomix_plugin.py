"""
This plugin imports recipes from the Thermomix recipe sites.
"""
from gourmet.plugin import PluginPlugin
from gourmet.importers.interactive_importer import ConvenientImporter
from gourmet.gdebug import warn
from gourmet.isoduration_parser import parse_iso8601_duration
from gourmet.importers.webextras import getdatafromurl
from collections import OrderedDict
from bs4 import BeautifulSoup, Tag
from fractions import Fraction
from gettext import gettext as _
from .state import WebsiteTestState
import re


class ThermomixParser(ConvenientImporter):
    """All recipe pages store the information in tags according to
    Recipe schema (defined in https://schema.org/Recipe).
    This parser extracts the recipe info and parses it.
    This is not a generic recipe parser since it relies on the
    specific implementation of the Thermomix websites.
    """

    def __init__(self, url, data, content_type):
        self.url = url
        self.data = data
        self.soup = BeautifulSoup(data, "html.parser")
        super(ThermomixParser, self).__init__()

    def do_run (self):
        """Construct recipe and ingredients from parsed data."""
        self.start_rec()
        # start_rec() initializes self.rec to an empty recipe dict
        self.rec['source'] = 'Web'
        self.rec['link'] = self.url
        parse_schema_recipe(self.soup, self.rec)
        ingredients = parse_schema_ingredients(self.soup)
        while ingredients:
            group, inglist = ingredients.popitem(last=False)
            if group:
                self.add_ing_group(group)
            else:
                self.group = None
            for txt in inglist:
                # add_ing_from_text(txt) uses self.db.parse_ingredient(txt)
                self.add_ing_from_text(txt)
        self.commit_rec()
        return super(ThermomixParser, self).do_run()


def parse_schema_recipe(soup, recipe):
    """Fill given recipe dict with data from HTML.

    @param soup: the parsed HTML data from BeautifulSoup
    @ptype soup: BeautifulSoup.Tag
    @param recipe: the gourmet recipe to fill
    @ptype recipe: dict
    @return: nothing, the recipe will be modified instead
    @rtype: None
    """
    nonempty = re.compile(r".+")
    tag = soup.find(itemprop="name", content=nonempty)
    if tag:
        recipe['title'] = tag["content"]
    tag = soup.find(itemprop="recipeCategory")
    if tag:
        recipe['category'] = tag.text
    tag = soup.find(itemprop="ratingValue", content=nonempty)
    if tag:
        rating = float(tag["content"])
        # adjust "1 to 5" rating to "1 to 10" of gourmet
        recipe['rating'] = int(rating * 2)
    tag = soup.find(itemprop="image", src=nonempty)
    if tag:
        image = tag["src"]
        recipe['image'], unused = getdatafromurl(image, content_type_check="image/")
    preptime = 0
    tag = soup.find(itemprop="performTime", content=nonempty)
    if tag:
        try:
            preptime = parse_iso8601_duration(tag['content'])
        except ValueError:
            warn("could not parse prepTime %r" % tag['content'])
        else:
            recipe['preptime'] = preptime
    tag = soup.find(itemprop="totalTime", content=nonempty)
    if tag:
        try:
            totaltime = parse_iso8601_duration(tag['content'])
        except ValueError:
            warn("could not parse prepTime %r" % tag['content'])
        else:
            # the cooking time is the difference between total and prep time
            recipe['cooktime'] = totaltime - preptime
    tag = soup.find(itemprop="recipeYield")
    if tag and tag.text:
        recipe['yields'] = tag.text.strip()
    tag = soup.find(itemprop="description")
    if tag:
        # replace images in the text with alternative text since they
        # are sometimes used in place
        for img in tag.find_all('img'):
            img.string = translate_image_text("["+get_alt_text(img)+"]")
        recipe['instructions'] = tag.get_text()
    tag = soup.find("div", attrs={"class": "tips"})
    if tag:
        p = tag.find("p")
        if p:
            recipe['modifications'] = p.text.strip()
    categories = soup.find_all(id="recipesCatFilterLink")
    if categories:
        cattext = ", ".join(cat.text.strip() for cat in categories)
        text = "%s %s" % (_("Category:"), cattext)
        if "modifications" in recipe:
            recipe["modifications"] += "\n\n" + text
        else:
            recipe["modifications"] = text


def get_alt_text(img):
    """Get alternative text from an image tag. The tag is searched
    in this order:
    1) find a non-empty alt="" attribute
    2) find a non-empty title="" attribute
    3) get the src="" filename (ie the part after the last "/")

    @param img: <img> tag
    @ptype img: BeautifulSoup.Tag
    @return: alternative text
    @rtype: string
    """
    alt = img.get("alt")
    if alt:
        return alt
    title = img.get("title")
    if title:
        return title
    src = img["src"]
    name = src.split("/")[-1]
    return name


def translate_image_text(text):
    """Replace known icon images with translated text.
    @param text: the image text to replace
    @ptype text: string
    @return: translated text if image text was known, else the original text
    @rtype: string
    """
    if text == "[Closed lid]":
        return _("[Closed lid]")
    if text == "[Dough mode]":
        return _("[Dough mode]")
    if text == "[Counter-clockwise operation]":
        return _("[Counter-clockwise operation]")
    if text == "[Gentle stir setting]":
        return _("[Gentle stir setting]")
    return text


def parse_schema_ingredients(soup):
    """Parse ingredient list with data from HTML.

    @param soup: the parsed HTML data from BeautifulSoup
    @ptype soup: BeautifulSoup.Tag
    @return: the grouped ingredients {group: ingredients}
    @rtype: OrderedDict {string, list}
    """
    # the ingredients are grouped, and the order of groups is preserved
    ingredients = OrderedDict()
    group = None
    inglist = ingredients.setdefault(group, [])
    section = soup.find(id="ingredient-section")
    # iterate recursively over all tags in the ingredient section
    # for each <p class="h5"> start a new group
    # for each <tag itemprop="recipeIngredient"> add a new ingredient
    for child in section.descendants:
        if isinstance(child, Tag):
            if child.name == "p" and has_css_class(child, "h5"):
                group = child.text.strip()
                inglist = ingredients.setdefault(group, [])
            elif child.get("itemprop", "") == "recipeIngredient":
                inglist.append(parse_schema_ingredient(child.text))
    return ingredients


def has_css_class(tag, cssclass):
    """Check if tag has given CSS class.
    @param tag: the HTML tag to check
    @ptype tag: BeautifulSoup.Tag
    @param cssclass: the CSS class name to search for
    @ptype cssclass: string
    @return: True if the CSS class is used in the class attribute
    @rtype: bool
    """
    classes = tag.get("class")
    if not classes:
        return False
    if isinstance(classes, list):
        return cssclass in classes
    return classes == cssclass


def parse_schema_ingredient(ing):
    """Parse one ingredient and return the corrected string
    suitable for ConvenientImporter.add_ing_from_text()

    @param ing: the ingredient
    @ptype ing: string
    @return: the adjusted ingredient string suitable for the default importer
    @rtype: string
    """
    split = ing.split(None, 1)
    if len(split) > 1:
        try:
            # replace german comma with dot
            amount = split[0].replace(',', '.')
            # convert to fraction
            amount = Fraction(amount)
            # convert to string so non-integer fractions can be parsed
            # by gourmet
            amount = str(amount)
            ing = "%s %s" % (amount, split[1])
        except ValueError:
            warn("could not parse amount %r" % split[0])
            # do nothing
            pass
    else:
        # do nothing
        pass
    return ing


class ThermomixPlugin(PluginPlugin):
    """This plugin matches for Thermomix recipe websites."""

    target_pluggable = 'webimport_plugin'

    def test_url(self, url, data):
        """Return positive integer if this URL should be parsed."""
        if ('rezeptwelt.de/' in url or
           'recipecommunity.com.au/' in url or
           'svetreceptu.cz/' in url or
           'mundodereceitasbimby.com.pt/' in url or
           'przepisownia.pl/' in url or
           'espace-recettes.fr/' in url or
           'ricettario-bimby.it/' in url or
           'recetario.es/' in url or
           'recipecommunity.co.uk/' in url):
            return WebsiteTestState.SUCCESS
        return WebsiteTestState.FAILED

    def get_importer(self, webpage_importer):
        """Use ThermomixParser instead of the default webpage_importer."""
        return ThermomixParser


def test_parser(url):
    """Try to parse a recipe for testing purposes."""
    from pprint import pprint
    data, url = getdatafromurl(url)
    pprint(url)
    soup = BeautifulSoup(data, "html.parser")
    recipe = {}
    parse_schema_recipe(soup, recipe)
    recipe['image'] = recipe['image'][:10] + '...'
    pprint(recipe, indent=2)
    ingredients = parse_schema_ingredients(soup)
    while ingredients:
        group, inglist = ingredients.popitem(last=False)
        if inglist:
            pprint((group, inglist), indent=2)


if __name__ == '__main__':
    # change the URL to test other recipes
    url = "https://www.rezeptwelt.de/backen-suess-rezepte/rhabarber-baiser-kuchen-mit-quarkfuellung/z8xv3npk-f73b6-406735-4a364-9x2wmxpq"
    test_parser(url)
