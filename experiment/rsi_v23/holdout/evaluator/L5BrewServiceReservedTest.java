package be.mjodheim.brewstead.service;

import be.mjodheim.brewstead.dto.brew.BatchResponse;
import be.mjodheim.brewstead.entity.Batch;
import be.mjodheim.brewstead.entity.PlayerProfile;
import be.mjodheim.brewstead.entity.Recipe;
import be.mjodheim.brewstead.enums.BatchStatus;
import be.mjodheim.brewstead.mapper.BrewMapper;
import be.mjodheim.brewstead.repository.BatchRepository;
import be.mjodheim.brewstead.repository.PlayerProfileRepository;
import be.mjodheim.brewstead.repository.RecipeIngredientRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Optional;

import static be.mjodheim.brewstead.TestData.player;
import static be.mjodheim.brewstead.TestData.recipe;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class L5BrewServiceReservedTest {

    @Mock BatchRepository batchRepository;
    @Mock PlayerProfileRepository playerProfileRepository;
    @Mock RecipeIngredientRepository recipeIngredientRepository;
    @Mock RecipeService recipeService;
    @Mock InventoryService inventoryService;
    @Mock BrewMapper brewMapper;
    @Mock EffectService effectService;
    @Mock ProgressionService progressionService;
    @InjectMocks BrewService service;

    @Test
    void twenty_two_percent_is_already_fermenting() {
        Batch batch = positionedBatch(22, 78);
        assertStatus(batch, BatchStatus.FERMENTING);
    }

    @Test
    void twenty_four_percent_is_already_fermenting() {
        Batch batch = positionedBatch(24, 76);
        assertStatus(batch, BatchStatus.FERMENTING);
    }

    @Test
    void eighty_two_percent_is_still_fermenting() {
        Batch batch = positionedBatch(82, 18);
        assertStatus(batch, BatchStatus.FERMENTING);
    }

    @Test
    void eighty_four_percent_is_still_fermenting() {
        Batch batch = positionedBatch(84, 16);
        assertStatus(batch, BatchStatus.FERMENTING);
    }

    private Batch positionedBatch(long elapsedSeconds, long remainingSeconds) {
        PlayerProfile player = player(1);
        Recipe recipe = recipe(2);
        LocalDateTime now = LocalDateTime.now();
        return Batch.builder()
                .id(7L)
                .player(player)
                .recipe(recipe)
                .startedAt(now.minusSeconds(elapsedSeconds))
                .readyAt(now.plusSeconds(remainingSeconds))
                .status(BatchStatus.BREWING)
                .build();
    }

    private void assertStatus(Batch batch, BatchStatus expected) {
        when(batchRepository.findById(7L)).thenReturn(Optional.of(batch));
        when(brewMapper.toResponse(any(Batch.class))).thenReturn((BatchResponse) null);
        service.updateBatchStatus(1L, 7L);
        assertEquals(expected, batch.getStatus());
    }
}
