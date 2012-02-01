"""Use PostgreSQL to extract a taxonomy out of DBpedia categories

Running this script will probably take around 30 minutes.

"""
# Author: Olivier Grisel <olivier.grisel@ensta.org>
# License: MIT

import logging
from os.path import join, sep
import dbpediakit.postgres as pg

FOLDER = __file__.rsplit(sep, 1)[0]
max_items = None  # set to None for processing the complete dumps
max_depth = 3


def candidate_article_processor(tuples):
    for source, target in tuples:
        yield (source, target, source[len("Category:"):])


updated = pg.check_link_table(
    "redirects", "redirects",
    predicate_filter="http://dbpedia.org/ontology/wikiPageRedirects",
    max_items=max_items)

updated &= pg.check_link_table(
    "skos_categories", "categories",
    predicate_filter="http://www.w3.org/2004/02/skos/core#broader",
    columns=(
        ('id', True),
        ('broader', True),
        ('candidate_article', True),
    ),
    processor=candidate_article_processor,
    max_items=max_items)

updated &= pg.check_link_table(
    "article_categories", "article_categories",
    predicate_filter="http://purl.org/dc/terms/subject")

updated &= pg.check_text_table(
    "long_abstracts", "long_abstracts", max_items=max_items)

if updated:
    pg.execute("ANALYZE")


# Load some aggregation function to manipulate arrays of arrays (to materialize
# paths to the roots in the taxonomy)
pg.check_run_if_undef(join(FOLDER, "array_aggregate.sql"))

# Aggregate categories info and find semantic grounding by trying to match with
# wikipedia articles
pg.check_run_if_undef(join(FOLDER, "build_grounded_categories.sql"))
pg.check_run_if_undef(join(FOLDER, "init_taxonomy.sql"))

current_depth = int(pg.select("SELECT max(depth) from taxonomy_dag"))
print current_depth
if current_depth < max_depth:
    for depth in range(current_depth + 1, max_depth + 1):
        logging.info("Growing taxonomy to depth=%d", depth)
        pg.check_run_if_undef(join(FOLDER, "grow_taxonomy.sql"))