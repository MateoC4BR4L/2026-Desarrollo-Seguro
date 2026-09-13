package com.cinebuscador.controller;

import com.cinebuscador.model.Pelicula;
import com.cinebuscador.repository.PeliculaRepository;
import jakarta.persistence.EntityNotFoundException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.MediaType;
import org.springframework.http.MediaTypeFactory;
import org.springframework.core.io.UrlResource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Controller
public class PeliculaController {

    private final PeliculaRepository peliculaRepo;

    @Value("${app.upload-dir}")
    private String uploadDir;

    public PeliculaController(PeliculaRepository peliculaRepo) {
        this.peliculaRepo = peliculaRepo;
    }

    @GetMapping("/")
    public String index(@RequestParam(required = false) String buscar,
                        @RequestParam(required = false, defaultValue = "nombre") String ordenarPor,
                        @RequestParam(required = false, defaultValue = "ASC") String sentido,
                        Model model) {

        if (buscar != null && !buscar.isBlank()) {
            List<Object[]> resultadosRaw;
            if ("DESC".equalsIgnoreCase(sentido)) {
                resultadosRaw = peliculaRepo.searchWithFuncionesDesc(buscar, ordenarPor);
            } else {
                resultadosRaw = peliculaRepo.searchWithFunciones(buscar, ordenarPor);
            }

            // Wrap Object[] in Maps for cleaner Thymeleaf access
            List<Map<String, Object>> resultados = new java.util.ArrayList<>();
            for (Object[] row : resultadosRaw) {
                Map<String, Object> map = new HashMap<>();
                map.put("id",        row[0]);
                map.put("nombre",    row[1]);
                map.put("fechaHora", row[2]);
                map.put("disponibles", row[3]);
                map.put("descripcion", row[4]);
                map.put("afichePath", row[5]);
                resultados.add(map);
            }
            model.addAttribute("resultados", resultados);
        }

        model.addAttribute("query", buscar != null ? buscar : "");
        model.addAttribute("sort_by", ordenarPor);
        model.addAttribute("sort_dir", sentido);
        return "index";
    }

    @GetMapping("/upload/{id}")
    public String uploadForm(@PathVariable Integer id, Model model) {
        Pelicula pelicula = peliculaRepo.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Pelicula no encontrada"));
        model.addAttribute("pelicula", pelicula);
        return "upload";
    }

    // --- MITIGACIÓN File Upload (CWE-434) ---
    // Extensiones permitidas (whitelist). Solo imágenes.
    private static final java.util.Set<String> ALLOWED_EXTENSIONS =
        java.util.Set.of(".jpg", ".jpeg", ".png", ".webp", ".gif");

    @PostMapping("/upload/{id}")
    public String uploadFile(@PathVariable Integer id,
                             @RequestParam("afiche") MultipartFile archivo,
                             Model model) throws IOException {

        Pelicula pelicula = peliculaRepo.findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Pelicula no encontrada"));

        // 1. Validar que el archivo no está vacío
        if (archivo.isEmpty()) {
            model.addAttribute("uploadError", "El archivo está vacío.");
            model.addAttribute("pelicula", pelicula);
            return "upload";
        }

        // 2. Extraer y validar la extensión contra la whitelist
        String originalName = archivo.getOriginalFilename() != null
            ? archivo.getOriginalFilename() : "";
        int dotIdx = originalName.lastIndexOf('.');
        if (dotIdx < 0) {
            model.addAttribute("uploadError", "El archivo no tiene extensión.");
            model.addAttribute("pelicula", pelicula);
            return "upload";
        }
        String ext = originalName.substring(dotIdx).toLowerCase();
        if (!ALLOWED_EXTENSIONS.contains(ext)) {
            model.addAttribute("uploadError",
                "Tipo de archivo no permitido. Solo se aceptan: jpg, jpeg, png, webp, gif.");
            model.addAttribute("pelicula", pelicula);
            return "upload";
        }

        // 3. Generar nombre seguro con UUID — el nombre original del cliente se descarta
        String safeFilename = java.util.UUID.randomUUID().toString() + ext;

        // 4. Protección contra path traversal: verificar que la ruta resuelta
        //    permanece dentro del directorio de uploads
        Path uploadPath = Paths.get(uploadDir).toAbsolutePath().normalize();
        if (!Files.exists(uploadPath)) {
            Files.createDirectories(uploadPath);
        }
        Path dest = uploadPath.resolve(safeFilename).normalize();
        if (!dest.startsWith(uploadPath)) {
            model.addAttribute("uploadError", "Ruta de archivo inválida.");
            model.addAttribute("pelicula", pelicula);
            return "upload";
        }

        // 5. Guardar usando el nombre seguro
        Files.copy(archivo.getInputStream(), dest);

        pelicula.setAfichePath(safeFilename);
        peliculaRepo.save(pelicula);

        return "redirect:/";
    }

    @GetMapping("/uploads/{filename:.+}")
    @ResponseBody
    public ResponseEntity<Resource> serveFile(@PathVariable String filename) throws IOException {
        Path filePath = Paths.get(uploadDir).toAbsolutePath().normalize()
            .resolve(filename).normalize();

        // Protección adicional: no servir archivos fuera del uploadDir
        if (!filePath.startsWith(Paths.get(uploadDir).toAbsolutePath().normalize())) {
            return ResponseEntity.badRequest().build();
        }

        Resource resource = new UrlResource(filePath.toUri());
        if (!resource.exists()) {
            return ResponseEntity.notFound().build();
        }

        MediaType mediaType = MediaTypeFactory.getMediaType(resource)
            .orElse(MediaType.APPLICATION_OCTET_STREAM);

        return ResponseEntity.ok()
            .contentType(mediaType)
            .header(HttpHeaders.CONTENT_DISPOSITION,
                "inline; filename=\"" + resource.getFilename() + "\"")
            .body(resource);
    }

}