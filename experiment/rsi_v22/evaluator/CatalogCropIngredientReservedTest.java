package be.mjodheim.brewstead.service;

import be.mjodheim.brewstead.dto.catalog.CropResponse;
import be.mjodheim.brewstead.entity.Crop;
import be.mjodheim.brewstead.entity.Ingredient;
import be.mjodheim.brewstead.enums.IngredientType;
import be.mjodheim.brewstead.repository.CropRepository;
import be.mjodheim.brewstead.repository.IngredientRepository;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static be.mjodheim.brewstead.TestData.ingredient;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class CatalogCropIngredientReservedTest {
    @Test
    void cropCatalogExposesTheIngredientNameRatherThanRepeatingTheCropName() {
        IngredientRepository ingredientRepository = mock(IngredientRepository.class);
        CropRepository cropRepository = mock(CropRepository.class);
        CatalogService service = new CatalogService(ingredientRepository, cropRepository);

        Ingredient barley = ingredient(5, IngredientType.CEREAL);
        barley.setName("Orge");
        Crop crop = Crop.builder()
                .id(8L)
                .name("Orge du Nord")
                .ingredient(barley)
                .growDurationMinutes(15)
                .yieldQuantity(new BigDecimal("3.500"))
                .build();
        when(cropRepository.findAll()).thenReturn(List.of(crop));

        List<CropResponse> crops = service.findAllCrops();

        assertEquals("Orge", crops.getFirst().ingredientName());
        assertEquals("Orge du Nord", crops.getFirst().name());
    }
}
