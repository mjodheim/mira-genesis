package be.mjodheim.brewstead.service;

import be.mjodheim.brewstead.dto.apiary.BeehiveResponse;
import be.mjodheim.brewstead.dto.farm.PlayerFieldResponse;
import be.mjodheim.brewstead.dto.game.GameStateResponse;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class GameStateEstateReservedTest {
    @Mock PlayerService playerService;
    @Mock FarmService farmService;
    @Mock ApiaryService apiaryService;
    @Mock InventoryService inventoryService;
    @Mock RecipeService recipeService;
    @Mock BrewService brewService;
    @Mock NpcOrderService npcOrderService;
    @InjectMocks GameStateService service;

    @Test
    void estateMetadataUsesTheServerFieldAndHivePriceSchedule() {
        when(farmService.findAllFields(7L)).thenReturn(List.of(
                mock(PlayerFieldResponse.class), mock(PlayerFieldResponse.class), mock(PlayerFieldResponse.class)));
        when(apiaryService.findAllHives(7L)).thenReturn(List.of(
                mock(BeehiveResponse.class), mock(BeehiveResponse.class)));

        GameStateResponse state = service.getState(7L);

        assertEquals(3, state.estate().fields());
        assertEquals(EstatePrices.MAX_FIELDS, state.estate().maxFields());
        assertEquals(EstatePrices.nextField(3), state.estate().fieldPrice());
        assertEquals(2, state.estate().hives());
        assertEquals(EstatePrices.MAX_HIVES, state.estate().maxHives());
        assertEquals(EstatePrices.nextHive(2), state.estate().hivePrice());
        assertEquals(EstatePrices.MAX_HIVE_LEVEL, state.estate().maxHiveLevel());
        assertEquals(EstatePrices.upgrades(), state.estate().hiveUpgradePrices());
    }
}
