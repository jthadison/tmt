#![allow(clippy::too_many_arguments)]
#![allow(clippy::redundant_field_names)] 
#![allow(clippy::uninlined_format_args)]
#![allow(clippy::new_without_default)]
#![allow(clippy::unwrap_or_default)]
#![allow(clippy::should_implement_trait)]
#![allow(clippy::to_string_trait_impl)]
#![allow(clippy::unnecessary_map_or)]
#![allow(clippy::redundant_closure)]
#![allow(clippy::manual_clamp)]
#![allow(clippy::map_flatten)]
#![allow(clippy::needless_borrow)]
#![allow(clippy::let_and_return)]
#![allow(clippy::large_enum_variant)]
#![allow(clippy::redundant_pattern_matching)]
#![allow(clippy::format_in_format_args)]
#![allow(clippy::match_like_matches_macro)]
#![allow(clippy::unnecessary_unwrap)]
#![allow(dead_code)]
#![allow(unused_imports)]
#![allow(unused_variables)]
#![allow(unused_mut)]
#![allow(unused_assignments)]

pub mod execution;
pub mod platforms;
pub mod risk;

// Temporarily disabled problematic modules
// pub mod api;
// pub mod messaging;
// pub mod utils;
// pub mod monitoring;

pub use platforms::PlatformType;
pub use risk::*;
