package be.mjodheim.brewstead.service;

import be.mjodheim.brewstead.entity.PlayerProfile;
import be.mjodheim.brewstead.entity.PlayerProgress;
import be.mjodheim.brewstead.enums.Specialization;
import be.mjodheim.brewstead.repository.PlayerAchievementRepository;
import be.mjodheim.brewstead.repository.PlayerProfileRepository;
import be.mjodheim.brewstead.repository.PlayerProgressRepository;
import org.junit.jupiter.api.Test;

import java.util.Optional;

import static be.mjodheim.brewstead.TestData.player;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class ProgressionMerchantReservedTest {
    @Test
    void merchantSpecializationAddsTenPercentToNpcCoinRewardOnly() {
        PlayerProgressRepository progressRepository = mock(PlayerProgressRepository.class);
        PlayerAchievementRepository achievementRepository = mock(PlayerAchievementRepository.class);
        PlayerProfileRepository playerRepository = mock(PlayerProfileRepository.class);
        ProgressionService service = new ProgressionService(progressRepository, achievementRepository, playerRepository);

        PlayerProfile merchant = player(1);
        PlayerProgress progress = PlayerProgress.builder()
                .player(merchant)
                .specialization(Specialization.MARCHAND)
                .build();
        when(progressRepository.findByPlayerId(1L)).thenReturn(Optional.of(progress));

        assertEquals(110, service.npcCoinReward(1L, 100));
        assertEquals(111, service.npcCoinReward(1L, 101));

        progress.setSpecialization(Specialization.CULTIVATEUR);
        assertEquals(100, service.npcCoinReward(1L, 100));
    }
}
