using Domain;
using Domain.Enums;

namespace BrewTrack.Tests;

/// <summary>
/// Formulation d'une recette. Ces valeurs sont les références du brassage amateur : un
/// brasseur doit pouvoir reconnaître ses propres chiffres, sinon la recette proposée par
/// Méli est jolie et infaisable.
/// </summary>
public class RecipeMathTests
{
    // ---- Fermentescibles ----------------------------------------------------

    [Fact]
    public void A_standard_20_liter_pale_ale_needs_about_four_and_a_half_kilos_of_malt()
    {
        // 20 L à 1.050, rendement 72 % : la référence du brassage amateur est ~4,5-4,7 kg.
        decimal kg = RecipeMath.FermentableKg(RecipeMath.GravityPoints(1.050m), 20m, IngredientType.Grain, 72m);

        Assert.InRange(kg, 4.4m, 4.8m);
    }

    [Fact]
    public void The_grain_bill_scales_with_the_volume()
    {
        // Le travers du modèle : proposer les mêmes 5 kg pour 20 L et pour 200 L.
        decimal small = RecipeMath.FermentableKg(50m, 20m, IngredientType.Grain, 72m);
        decimal big = RecipeMath.FermentableKg(50m, 200m, IngredientType.Grain, 72m);

        // (à l'arrondi au gramme près, chaque masse étant arrondie séparément)
        Assert.InRange(big, small * 10m - 0.01m, small * 10m + 0.01m);
    }

    [Fact]
    public void The_grain_bill_scales_with_the_target_gravity()
    {
        decimal light = RecipeMath.FermentableKg(RecipeMath.GravityPoints(1.040m), 20m, IngredientType.Grain, 72m);
        decimal strong = RecipeMath.FermentableKg(RecipeMath.GravityPoints(1.080m), 20m, IngredientType.Grain, 72m);

        Assert.InRange(strong, light * 2m - 0.01m, light * 2m + 0.01m);
    }

    [Fact]
    public void A_20_liter_mead_needs_about_six_kilos_of_honey()
    {
        // Hydromel classique : 20 L à 1.100 ≈ 6 kg de miel (~300 g/L).
        decimal kg = RecipeMath.FermentableKg(RecipeMath.GravityPoints(1.100m), 20m, IngredientType.Honey, 72m);

        Assert.InRange(kg, 5.5m, 6.5m);
    }

    [Fact]
    public void Honey_and_sugar_ignore_the_mash_efficiency()
    {
        // Le miel se dissout entièrement : lui appliquer le rendement du grain sous-doserait
        // un hydromel de près de 30 %.
        Assert.False(RecipeMath.NeedsMashing(IngredientType.Honey));
        Assert.True(RecipeMath.NeedsMashing(IngredientType.Grain));

        decimal at72 = RecipeMath.FermentableKg(100m, 20m, IngredientType.Honey, 72m);
        decimal at100 = RecipeMath.FermentableKg(100m, 20m, IngredientType.Honey, 100m);
        Assert.Equal(at72, at100);

        Assert.NotEqual(
            RecipeMath.FermentableKg(100m, 20m, IngredientType.Grain, 72m),
            RecipeMath.FermentableKg(100m, 20m, IngredientType.Grain, 100m));
    }

    [Fact]
    public void A_poor_efficiency_means_more_malt()
    {
        decimal good = RecipeMath.FermentableKg(50m, 20m, IngredientType.Grain, 80m);
        decimal poor = RecipeMath.FermentableKg(50m, 20m, IngredientType.Grain, 60m);

        Assert.True(poor > good);
    }

    [Theory]
    [InlineData(IngredientType.Hop)]
    [InlineData(IngredientType.Yeast)]
    [InlineData(IngredientType.Water)]
    public void What_brings_no_sugar_cannot_reach_a_target_gravity(IngredientType type)
    {
        Assert.Throws<ArgumentException>(() => RecipeMath.FermentableKg(50m, 20m, type, 72m));
    }

    // ---- Houblons (Tinseth) -------------------------------------------------

    [Fact]
    public void A_20_liter_pale_ale_at_35_ibu_needs_about_fifty_grams_of_hops()
    {
        // 20 L, 1.050, houblon à 6 % d'acides alpha, 60 min : ~50 g. C'est LA valeur qu'un
        // brasseur reconnaît ; le modèle proposait aussi bien 20 g que 300 g.
        decimal grams = RecipeMath.HopGrams(35m, 20m, 6m, 1.050m, 60);

        Assert.InRange(grams, 45m, 56m);
    }

    [Fact]
    public void A_stronger_hop_means_a_smaller_dose()
    {
        decimal mild = RecipeMath.HopGrams(35m, 20m, 4m, 1.050m, 60);
        decimal strong = RecipeMath.HopGrams(35m, 20m, 12m, 1.050m, 60);

        Assert.True(strong < mild);
        decimal proportional = Math.Round(mild * 4m / 12m, 1);
        Assert.InRange(strong, proportional - 1m, proportional + 1m);
    }

    [Fact]
    public void A_short_boil_extracts_less_bitterness()
    {
        // 15 min amérise bien moins que 60 min : il en faut davantage pour les mêmes IBU.
        decimal long_ = RecipeMath.HopGrams(35m, 20m, 6m, 1.050m, 60);
        decimal short_ = RecipeMath.HopGrams(35m, 20m, 6m, 1.050m, 15);

        Assert.True(short_ > long_ * 1.5m);
    }

    [Fact]
    public void A_denser_wort_extracts_less_bitterness()
    {
        Assert.True(RecipeMath.HopUtilization(1.080m, 60) < RecipeMath.HopUtilization(1.040m, 60));
    }

    [Fact]
    public void Hop_mass_and_ibu_are_two_readings_of_the_same_calculation()
    {
        decimal grams = RecipeMath.HopGrams(40m, 20m, 6.5m, 1.055m, 60);
        decimal ibu = RecipeMath.IbuFromHops(grams, 20m, 6.5m, 1.055m, 60);

        Assert.InRange(ibu, 39.5m, 40.5m);
    }

    [Fact]
    public void A_dry_hop_addition_brings_no_bitterness()
    {
        Assert.Equal(0m, RecipeMath.HopUtilization(1.050m, 0));
        Assert.Equal(0m, RecipeMath.IbuFromHops(100m, 20m, 6m, 1.050m, 0));
    }

    // ---- Densité finale, alcool, levure, eau --------------------------------

    [Fact]
    public void A_beer_at_1_050_finishes_around_1_012_and_five_degrees()
    {
        decimal fg = RecipeMath.EstimateFinalGravity(1.050m, 75m);
        Assert.InRange(fg, 1.011m, 1.015m);

        decimal abv = BrewMath.AbvFromGravities(1.050m, fg);
        Assert.InRange(abv, 4.5m, 5.3m);
    }

    [Fact]
    public void A_more_attenuative_yeast_gives_a_drier_beer_and_more_alcohol()
    {
        decimal lazy = RecipeMath.EstimateFinalGravity(1.060m, 65m);
        decimal hungry = RecipeMath.EstimateFinalGravity(1.060m, 85m);

        Assert.True(hungry < lazy);
        Assert.True(BrewMath.AbvFromGravities(1.060m, hungry) > BrewMath.AbvFromGravities(1.060m, lazy));
    }

    [Fact]
    public void A_20_liter_batch_takes_one_sachet_of_dry_yeast()
    {
        // Un sachet du commerce fait 11,5 g : ~10 g pour 20 L en densité normale.
        Assert.Equal(10m, RecipeMath.DryYeastGrams(20m, 1.048m));
        // Moût dense : on double la dose.
        Assert.Equal(20m, RecipeMath.DryYeastGrams(20m, 1.075m));
    }

    [Fact]
    public void The_water_needed_exceeds_the_final_volume()
    {
        // 20 L en cuve ne se font pas avec 20 L d'eau : le grain en absorbe et l'ébullition en évapore.
        decimal water = RecipeMath.TotalWaterLiters(20m, 4.6m, 60);

        Assert.InRange(water, 26m, 29m);
    }

    // ---- Garde-fou de vraisemblance -----------------------------------------

    [Theory]
    [InlineData(4.6, Unit.Kilogram, IngredientType.Grain)]      // 230 g/L : normal
    [InlineData(50.0, Unit.Gram, IngredientType.Hop)]           // 2,5 g/L : normal
    [InlineData(11.5, Unit.Gram, IngredientType.Yeast)]         // 0,6 g/L : normal
    [InlineData(6.0, Unit.Kilogram, IngredientType.Honey)]      // 300 g/L : hydromel
    [InlineData(400.0, Unit.Gram, IngredientType.Hop)]          // 20 g/L : NEIPA très houblonnée
    public void A_realistic_quantity_passes(double quantity, Unit unit, IngredientType type)
    {
        Assert.Null(RecipeMath.ImplausibleQuantity(type, (decimal)quantity, unit, 20m));
    }

    [Theory]
    [InlineData(50.0, Unit.Kilogram, IngredientType.Grain)]     // 50 kg dans 20 L
    [InlineData(5.0, Unit.Gram, IngredientType.Grain)]          // 5 g de malt pour 20 L
    [InlineData(2.0, Unit.Kilogram, IngredientType.Hop)]        // 100 g/L de houblon
    [InlineData(1.0, Unit.Kilogram, IngredientType.Yeast)]      // 1 kg de levure
    public void An_absurd_quantity_is_caught_with_an_explanation(double quantity, Unit unit, IngredientType type)
    {
        string? why = RecipeMath.ImplausibleQuantity(type, (decimal)quantity, unit, 20m);

        Assert.NotNull(why);
        Assert.Contains("g/L", why);
        Assert.Contains("plan_recipe", why);
    }

    [Fact]
    public void The_plausible_range_follows_the_batch_volume()
    {
        // 46 kg de malt : aberrant dans 20 L, parfaitement normal dans 200 L.
        Assert.NotNull(RecipeMath.ImplausibleQuantity(IngredientType.Grain, 46m, Unit.Kilogram, 20m));
        Assert.Null(RecipeMath.ImplausibleQuantity(IngredientType.Grain, 46m, Unit.Kilogram, 200m));
    }

    [Fact]
    public void Water_and_other_are_not_second_guessed()
    {
        Assert.Null(RecipeMath.ImplausibleQuantity(IngredientType.Water, 30m, Unit.Liter, 20m));
        Assert.Null(RecipeMath.ImplausibleQuantity(IngredientType.Other, 0.001m, Unit.Gram, 20m));
    }

    [Fact]
    public void A_liter_counts_as_a_kilo()
    {
        // Convention de l'application, déjà annoncée au modèle pour les coûts.
        Assert.Equal(1000m, RecipeMath.ToGrams(1m, Unit.Liter));
        Assert.Equal(1000m, RecipeMath.ToGrams(1m, Unit.Kilogram));
    }
}
