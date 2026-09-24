using Domain;
using Domain.Enums;

namespace BrewTrack.Tests;

public class L5RecipeMathReservedTests
{
    [Fact]
    public void Milligrams_convert_to_fractional_grams()
    {
        Assert.Equal(0.5m, RecipeMath.ToGrams(500m, Unit.Milligram));
    }

    [Fact]
    public void Milligram_conversion_preserves_decimal_scale()
    {
        Assert.Equal(1.25m, RecipeMath.ToGrams(1250m, Unit.Milligram));
    }

    [Fact]
    public void Water_plan_keeps_tenth_liter_precision()
    {
        Assert.Equal(27.4m, RecipeMath.TotalWaterLiters(20m, 4.6m, 60));
    }

    [Fact]
    public void Water_plan_keeps_half_liter_boundary()
    {
        Assert.Equal(32.5m, RecipeMath.TotalWaterLiters(25m, 5.25m, 30));
    }
}
