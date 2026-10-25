package com.cinebuscador;

import com.cinebuscador.controller.AuthController;
import com.cinebuscador.model.User;
import com.cinebuscador.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.ui.ExtendedModelMap;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

// Pruebas unitarias del Ejercicio 5 (almacenamiento inseguro de contrasenas).
// Antes se guardaba con AES/ECB y una clave fija en el codigo -> reversible.
// La mitigacion usa un hash BCrypt (una via, con salt).
//
// Uso un UserRepository mockeado para no levantar base ni Spring. Al registrar
// un usuario capturo lo que se iba a guardar y lo reviso.
//   mvn test        (desde Ejercicio5)
class AuthControllerPasswordStorageTest {

    // Formato de un hash BCrypt: $2a/2b/2y, coste de 2 digitos y 53 caracteres mas.
    private static final String BCRYPT_REGEX = "^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$";

    private String registrarYObtenerPassword(String username, String password) {
        UserRepository repo = mock(UserRepository.class);
        when(repo.findByUsername(anyString())).thenReturn(Optional.empty());

        AuthController controller = new AuthController(repo);
        controller.register(username, password, password, new ExtendedModelMap());

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(repo).save(captor.capture());
        return captor.getValue().getPassword();
    }

    @Test
    @DisplayName("La contrasena se guarda como hash BCrypt, no cifrada ni en texto plano")
    void passwordSeGuardaComoHashBcrypt() {
        String plano = "Password123!";
        String guardada = registrarYObtenerPassword("usuario_bcrypt", plano);

        assertFalse(guardada.equals(plano), "Se guardo la contrasena en texto plano.");
        assertTrue(guardada.matches(BCRYPT_REGEX),
                "Lo guardado no es un hash BCrypt, sigue siendo reversible: " + guardada);
    }

    @Test
    @DisplayName("Misma contrasena, hashes distintos (hay salt; ECB daria el mismo)")
    void mismaPasswordProduceHashesDistintos() {
        UserRepository repo = mock(UserRepository.class);
        when(repo.findByUsername(anyString())).thenReturn(Optional.empty());

        AuthController controller = new AuthController(repo);
        controller.register("usuario_a", "ClaveRepetida1", "ClaveRepetida1", new ExtendedModelMap());
        controller.register("usuario_b", "ClaveRepetida1", "ClaveRepetida1", new ExtendedModelMap());

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(repo, times(2)).save(captor.capture());

        String hashA = captor.getAllValues().get(0).getPassword();
        String hashB = captor.getAllValues().get(1).getPassword();

        assertFalse(hashA.equals(hashB),
                "Dos usuarios con la misma contrasena quedaron con el mismo valor: es ECB, sin salt.");
    }
}
