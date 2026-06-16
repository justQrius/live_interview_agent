#[cfg(test)]
mod tests {
    #[test]
    fn test_platform_detection() {
        #[cfg(target_os = "windows")]
        assert!(cfg!(target_os = "windows"));
        
        #[cfg(target_os = "macos")]
        assert!(cfg!(target_os = "macos"));
        
        #[cfg(target_os = "linux")]
        assert!(cfg!(target_os = "linux"));
    }
}
