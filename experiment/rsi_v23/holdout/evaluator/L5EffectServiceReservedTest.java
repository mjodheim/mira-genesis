package be.mjodheim.brewstead.service;

import be.mjodheim.brewstead.entity.PlayerEffect;
import be.mjodheim.brewstead.enums.EffectKind;
import be.mjodheim.brewstead.repository.PlayerEffectRepository;
import be.mjodheim.brewstead.repository.PlayerProfileRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class L5EffectServiceReservedTest {

    @Mock PlayerEffectRepository effectRepository;
    @Mock PlayerProfileRepository playerRepository;
    @InjectMocks EffectService service;

    @Test
    void qualityShift_truncates_each_effect_independently_case_one() {
        mockMagnitudes(30, 11, 0);
        assertEquals(10, service.qualityShift(1L));
    }

    @Test
    void qualityShift_truncates_each_effect_independently_case_two() {
        mockMagnitudes(32, 11, 0);
        assertEquals(11, service.qualityShift(1L));
    }

    @Test
    void coin_boost_uses_integer_percentage_semantics_case_one() {
        mockMagnitudes(0, 0, 25);
        assertEquals(123, service.boostCoins(1L, 99));
    }

    @Test
    void coin_boost_uses_integer_percentage_semantics_case_two() {
        mockMagnitudes(0, 0, 50);
        assertEquals(151, service.boostCoins(1L, 101));
    }

    private void mockMagnitudes(int inspiration, int heavyHand, int purse) {
        when(effectRepository.findFirstByPlayerIdAndKindAndExpiresAtAfter(
                eq(1L), any(EffectKind.class), any(LocalDateTime.class)))
                .thenAnswer(invocation -> {
                    EffectKind kind = invocation.getArgument(1);
                    int magnitude = switch (kind) {
                        case INSPIRATION -> inspiration;
                        case MAIN_LOURDE -> heavyHand;
                        case BOURSE_PERCEE -> purse;
                        default -> 0;
                    };
                    if (magnitude == 0) {
                        return Optional.empty();
                    }
                    return Optional.of(PlayerEffect.builder()
                            .kind(kind)
                            .magnitude(magnitude)
                            .startedAt(LocalDateTime.now().minusMinutes(1))
                            .expiresAt(LocalDateTime.now().plusMinutes(1))
                            .build());
                });
    }
}
