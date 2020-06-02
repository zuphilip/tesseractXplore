import asyncio
from logging import getLogger

from pyinaturalist.node_api import get_taxa
from naturtag.constants import ICONIC_TAXA, RANKS
from naturtag.models import Taxon
from naturtag.app import get_app
from naturtag.widgets import DropdownTextField, IconicTaxaIcon, TaxonListItem

logger = getLogger().getChild(__name__)


class TaxonSearchController:
    """ Controller class to manage taxon search """
    def __init__(self, screen):
        self.search_tab = screen.search_tab
        self.search_results_tab = screen.search_results_tab

        # Search inputs
        self.taxon_id_input = screen.search_tab.ids.taxon_id_input
        self.taxon_id_input.bind(on_text_validate=self.on_taxon_id)
        self.taxon_search_input = screen.search_tab.ids.taxon_search_input
        self.taxon_search_input.selection_callback = self.on_select_search_result
        self.exact_rank_input = screen.search_tab.ids.exact_rank_input
        self.min_rank_input = screen.search_tab.ids.min_rank_input
        self.max_rank_input = screen.search_tab.ids.max_rank_input
        self.iconic_taxa_filters = screen.search_tab.ids.iconic_taxa

        # 'Categories' (iconic taxa) icons
        for id in ICONIC_TAXA:
            icon = IconicTaxaIcon(id)
            icon.bind(on_release=self.on_select_iconic_taxon)
            self.iconic_taxa_filters.add_widget(icon)

        # Search inputs with dropdowns
        self.rank_menus = (
            DropdownTextField(text_input=self.exact_rank_input, text_items=RANKS),
            DropdownTextField(text_input=self.min_rank_input, text_items=RANKS),
            DropdownTextField(text_input=self.max_rank_input, text_items=RANKS),
        )

        # Buttons
        self.taxon_search_button = screen.search_tab.ids.taxon_search_button
        self.taxon_search_button.bind(on_release=self.search)
        self.search_input_clear_button = self.taxon_search_input.ids.search_input_clear_button
        self.search_input_clear_button.bind(on_release=self.taxon_search_input.reset)
        self.reset_search_button = screen.search_tab.ids.reset_search_button
        self.reset_search_button.bind(on_release=self.reset_all_search_inputs)

        # Search results
        self.search_results_list = self.search_results_tab.ids.search_results_list

    @property
    def selected_iconic_taxa(self):
        return [t for t in self.iconic_taxa_filters.children if t.is_selected]

    def search(self, *args):
        """ Run a search with the currently selected search parameters """
        asyncio.run(self._search())

    # TODO: Paginated results
    async def _search(self):
        # TODO: To make async HTTP requests, Pick one of: grequests, aiohttp, twisted, tornado...
        # async def _get_taxa(params):
        #     return get_taxa(**params)['results']

        params = self.get_search_parameters()
        logger.info(f'Searching taxa with parameters: {params}')
        # results = await _get_taxa(params)
        results = get_taxa(**params)['results']
        logger.info(f'Found {len(results)} search results')
        await self.update_search_results(results)

    def get_search_parameters(self):
        """ Get API-compatible search parameters from the input widgets """
        params = {
            'q': self.taxon_search_input.input.text,
            'taxon_id': [t.taxon_id for t in self.selected_iconic_taxa],
            'rank': self.exact_rank_input.text,
            'min_rank': self.min_rank_input.text,
            'max_rank': self.max_rank_input.text,
            'per_page': 30,
            'locale': get_app().locale,
            'preferred_place_id': get_app().preferred_place_id,
        }
        return {k: v for k, v in params.items() if v}

    async def update_search_results(self, results):
        self.search_results_list.clear_widgets()
        for taxon_dict in results:
            item = TaxonListItem(taxon=Taxon.from_dict(taxon_dict), parent_tab=self.search_results_tab)
            self.search_results_list.add_widget(item)

    def reset_all_search_inputs(self, *args):
        logger.info('Resetting search filters')
        self.taxon_search_input.reset()
        for t in self.selected_iconic_taxa:
            t.toggle_selection()
        self.exact_rank_input.text = ''
        self.min_rank_input.text = ''
        self.max_rank_input.text = ''

    @staticmethod
    def on_select_iconic_taxon(button):
        """ Handle clicking an iconic taxon; don't re-select the taxon if we're de-selecting it """
        if not button.is_selected:  # Note: this is the state *after* the click event
            get_app().select_taxon(id=button.taxon_id)

    @staticmethod
    def on_select_search_result(metadata: dict):
        """ Handle clicking a taxon from autocomplete dropdown """
        get_app().select_taxon(taxon_dict=metadata)

    @staticmethod
    def on_taxon_id(text_input):
        """ Handle entering a taxon ID and pressing Enter """
        get_app().select_taxon(id=int(text_input.text))
